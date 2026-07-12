import 'dart:math';

import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart' as ll;
import 'package:maplibre_gl/maplibre_gl.dart';

import '../core/api_config.dart';
import '../models/floor_plan.dart';

const _tileSourceId = 'floor-tiles';
const _routeSourceId = 'floor-route';
const _markersSourceId = 'floor-markers';
const _storesFillLayerId = 'floor-stores-fill';

/// 지도 위에 얹을 현재 위치/목적지 점 마커. 종류에 따라 스타일이 달라진다
/// (마커 색상은 [_markersGeoJson]의 circle-color data-driven 표현식이 결정).
enum MapMarkerKind { current, destination }

/// 매장 폴리곤을 탭할 수 있는 실내 평면도 뷰.
///
/// 건물/층의 벡터 타일(MVT, `GET /buildings/{id}/floors/{floor}/tiles/{z}/{x}/{y}.mvt`)을
/// MapLibre GL 벡터 소스로 얹어서 외곽선·매장·POI를 그린다. 매장 이름 라벨은
/// MapLibre 심볼 레이어(`text-max-width` + 충돌 감지)가 자동 배치하므로,
/// 예전처럼 폴리곤 픽셀 크기에 맞춰 폰트를 직접 계산하다가 텍스트가 박스를
/// 벗어나는 문제가 생기지 않는다.
///
/// 경로선과 현재 위치/목적지 마커는 벡터 타일과 별개로 GeoJSON 소스에
/// 얹는다 — 다익스트라 결과가 바뀔 때마다 소스 데이터만 교체한다.
class FloorPlanView extends StatefulWidget {
  const FloorPlanView({
    super.key,
    required this.buildingId,
    required this.floorName,
    required this.floorPlan,
    this.onStoreSelected,
    this.currentLocation,
    this.destination,
    this.routePoints = const [],
  });

  final String buildingId;
  final String floorName;
  final FloorPlan floorPlan;
  final ValueChanged<StorePolygon>? onStoreSelected;

  /// 현재 위치 마커. null이면 표시하지 않는다.
  final ll.LatLng? currentLocation;

  /// 목적지 마커. null이면 표시하지 않는다.
  final ll.LatLng? destination;

  /// 시작점→목적지 경로선. 2개 미만이면 그리지 않는다.
  final List<ll.LatLng> routePoints;

  @override
  State<FloorPlanView> createState() => _FloorPlanViewState();
}

class _FloorPlanViewState extends State<FloorPlanView> {
  MapLibreMapController? _controller;
  bool _styleReady = false;

  @override
  Widget build(BuildContext context) {
    return MapLibreMap(
      styleString: _initialStyle,
      initialCameraPosition: CameraPosition(
        target: _initialCenter(widget.floorPlan),
        zoom: 18,
      ),
      onMapCreated: (controller) => _controller = controller,
      onStyleLoadedCallback: _onStyleLoaded,
      onMapClick: _handleMapClick,
      compassEnabled: false,
      myLocationEnabled: false,
      logoEnabled: false,
      attributionButtonPosition: AttributionButtonPosition.bottomRight,
    );
  }

  @override
  void didUpdateWidget(covariant FloorPlanView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!_styleReady) return;
    if (oldWidget.buildingId != widget.buildingId ||
        oldWidget.floorName != widget.floorName) {
      // 건물/층이 바뀌면 위젯을 통째로 다시 만드는 편이 안전하므로
      // (다른 key로 재생성됨) 여기서는 데이터만 갱신되는 경우만 다룬다.
      return;
    }
    if (oldWidget.routePoints != widget.routePoints) {
      _updateRouteSource();
    }
    if (oldWidget.currentLocation != widget.currentLocation ||
        oldWidget.destination != widget.destination) {
      _updateMarkersSource();
    }
  }

  Future<void> _onStyleLoaded() async {
    final controller = _controller;
    if (controller == null) return;

    final tileUrl =
        '$apiBaseUrl/buildings/${widget.buildingId}/floors/${widget.floorName}/tiles/{z}/{x}/{y}.mvt';

    await controller.addSource(
      _tileSourceId,
      VectorSourceProperties(tiles: [tileUrl]),
    );

    // 원본 SVG 디자인(hyundai_floor_map_corrected_v6.svg)의 색상을 그대로 옮긴다.
    await controller.addFillLayer(
      _tileSourceId,
      'floor-footprint-fill',
      const FillLayerProperties(
        fillColor: '#FFFFFF',
        fillOutlineColor: '#00000088',
      ),
      sourceLayer: 'footprint',
      enableInteraction: false,
    );
    await controller.addFillLayer(
      _tileSourceId,
      _storesFillLayerId,
      const FillLayerProperties(
        fillColor: '#F3F1EF',
        fillOutlineColor: '#D8D4D1',
      ),
      sourceLayer: 'stores',
    );
    // 매장명 라벨: 폴리곤 크기에 맞춰 폰트를 직접 계산하던 예전 로직 대신
    // MapLibre의 자동 줄바꿈(text-max-width)과 충돌 감지에 맡긴다 —
    // 이게 벡터 타일로 바꾼 핵심 이유(텍스트가 매장 박스를 벗어나는 문제)다.
    await controller.addSymbolLayer(
      _tileSourceId,
      'floor-stores-label',
      SymbolLayerProperties(
        textField: ['get', 'name'],
        textSize: [
          'interpolate',
          ['linear'],
          ['zoom'],
          16,
          9,
          20,
          14,
        ],
        textMaxWidth: 6,
        textVariableAnchor: const ['center'],
        textColor: '#444846',
        textHaloColor: '#FFFFFF',
        textHaloWidth: 1.2,
        symbolAvoidEdges: true,
        textAllowOverlap: false,
      ),
      sourceLayer: 'stores',
      enableInteraction: false,
    );

    await controller.addCircleLayer(
      _tileSourceId,
      'floor-pois-circle',
      const CircleLayerProperties(
        circleRadius: 4,
        circleColor: '#76AE6D',
        circleStrokeColor: '#FFFFFF',
        circleStrokeWidth: 1.2,
      ),
      sourceLayer: 'pois',
      enableInteraction: false,
    );
    await controller.addSymbolLayer(
      _tileSourceId,
      'floor-pois-label',
      const SymbolLayerProperties(
        textField: ['get', 'name'],
        textSize: 10,
        textOffset: [0, 1.2],
        textColor: '#4F5451',
        textHaloColor: '#FFFFFF',
        textHaloWidth: 1,
      ),
      sourceLayer: 'pois',
      enableInteraction: false,
    );

    await controller.addGeoJsonSource(_routeSourceId, _emptyFeatureCollection);
    await controller.addLineLayer(
      _routeSourceId,
      'floor-route-line',
      const LineLayerProperties(
        lineColor: '#1A73E8',
        lineWidth: 5,
        lineCap: 'round',
        lineJoin: 'round',
      ),
      enableInteraction: false,
    );

    await controller.addGeoJsonSource(_markersSourceId, _emptyFeatureCollection);
    await controller.addCircleLayer(
      _markersSourceId,
      'floor-markers-circle',
      const CircleLayerProperties(
        circleRadius: 8,
        circleColor: [
          'match',
          ['get', 'kind'],
          'destination',
          '#E53935',
          '#6C3FE0',
        ],
        circleStrokeColor: '#FFFFFF',
        circleStrokeWidth: 2,
      ),
      enableInteraction: false,
    );

    _styleReady = true;
    await _updateRouteSource();
    await _updateMarkersSource();
    await _fitToFootprint();
  }

  Future<void> _fitToFootprint() async {
    final controller = _controller;
    final footprint = widget.floorPlan.footprint;
    if (controller == null || footprint.isEmpty) return;

    var south = footprint.first.latitude;
    var north = footprint.first.latitude;
    var west = footprint.first.longitude;
    var east = footprint.first.longitude;
    for (final point in footprint) {
      south = south < point.latitude ? south : point.latitude;
      north = north > point.latitude ? north : point.latitude;
      west = west < point.longitude ? west : point.longitude;
      east = east > point.longitude ? east : point.longitude;
    }

    await controller.moveCamera(
      CameraUpdate.newLatLngBounds(
        LatLngBounds(
          southwest: LatLng(south, west),
          northeast: LatLng(north, east),
        ),
        left: 24,
        top: 24,
        right: 24,
        bottom: 24,
      ),
    );
  }

  Future<void> _updateRouteSource() async {
    final controller = _controller;
    if (controller == null) return;
    final points = widget.routePoints;
    if (points.length < 2) {
      await controller.setGeoJsonSource(_routeSourceId, _emptyFeatureCollection);
      return;
    }
    await controller.setGeoJsonSource(_routeSourceId, {
      'type': 'FeatureCollection',
      'features': [
        {
          'type': 'Feature',
          'properties': const <String, dynamic>{},
          'geometry': {
            'type': 'LineString',
            'coordinates': [
              for (final point in points) [point.longitude, point.latitude],
            ],
          },
        },
      ],
    });
  }

  Future<void> _updateMarkersSource() async {
    final controller = _controller;
    if (controller == null) return;
    final features = <Map<String, dynamic>>[];
    final current = widget.currentLocation;
    final destination = widget.destination;
    if (current != null) {
      features.add(_markerFeature(current, MapMarkerKind.current));
    }
    if (destination != null) {
      features.add(_markerFeature(destination, MapMarkerKind.destination));
    }
    await controller.setGeoJsonSource(_markersSourceId, {
      'type': 'FeatureCollection',
      'features': features,
    });
  }

  Map<String, dynamic> _markerFeature(ll.LatLng point, MapMarkerKind kind) {
    return {
      'type': 'Feature',
      'properties': {'kind': kind.name},
      'geometry': {
        'type': 'Point',
        'coordinates': [point.longitude, point.latitude],
      },
    };
  }

  Future<void> _handleMapClick(Point<double> point, LatLng coordinates) async {
    final controller = _controller;
    final onStoreSelected = widget.onStoreSelected;
    if (controller == null || onStoreSelected == null) return;

    final features = await controller.queryRenderedFeatures(
      point,
      [_storesFillLayerId],
      null,
    );
    if (features.isEmpty) return;

    final properties = (features.first as Map)['properties'] as Map?;
    final id = properties?['id'] as String?;
    if (id == null) return;

    final store = widget.floorPlan.stores.where((s) => s.id == id).firstOrNull;
    if (store != null) onStoreSelected(store);
  }

  LatLng _initialCenter(FloorPlan floorPlan) {
    if (floorPlan.footprint.isNotEmpty) {
      return _toMapLibreLatLng(floorPlan.footprint.first);
    }
    if (floorPlan.stores.isNotEmpty) {
      return _toMapLibreLatLng(floorPlan.stores.first.centroid);
    }
    if (floorPlan.pois.isNotEmpty) {
      return _toMapLibreLatLng(floorPlan.pois.first.point);
    }
    return const LatLng(37.5665, 126.9780); // fallback: 서울시청
  }

  static LatLng _toMapLibreLatLng(ll.LatLng point) {
    return LatLng(point.latitude, point.longitude);
  }
}

const _emptyFeatureCollection = {'type': 'FeatureCollection', 'features': <Map<String, dynamic>>[]};

// 원본 SVG(hyundai_floor_map_corrected_v6.svg)의 배경색을 그대로 옮겼다.
// 나머지 레이어(외곽선/매장/POI/경로)는 스타일 로드 후 벡터·GeoJSON
// 소스로 추가한다.
const _initialStyle = '''
{
  "version": 8,
  "sources": {},
  "layers": [
    {"id": "background", "type": "background", "paint": {"background-color": "#EDF4E7"}}
  ]
}
''';
