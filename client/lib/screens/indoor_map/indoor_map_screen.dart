import 'package:flutter/material.dart';

import '../../core/service_locator.dart';
import '../../models/building.dart';
import '../../routing/app_routes.dart';

class IndoorMapScreen extends StatefulWidget {
  const IndoorMapScreen({super.key});

  @override
  State<IndoorMapScreen> createState() => _IndoorMapScreenState();
}

class _IndoorMapScreenState extends State<IndoorMapScreen> {
  late final Future<Building?> _buildingFuture;

  @override
  void initState() {
    super.initState();
    _buildingFuture = buildingRepository.getBuilding('bldg-001');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('실내 지도 (PDR 모드)')),
      body: Center(
        child: FutureBuilder<Building?>(
          future: _buildingFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const CircularProgressIndicator();
            }
            final building = snapshot.data;
            if (building == null) {
              return const Text('건물 정보를 찾을 수 없습니다');
            }
            return Text(
              '${building.name} · ${building.floors.length}개 층\n'
              '(평면도 GeoJSON 렌더링 예정)',
              textAlign: TextAlign.center,
            );
          },
        ),
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: FilledButton(
            onPressed: () {
              Navigator.of(context).pushNamed(AppRoutes.destination);
            },
            child: const Text('목적지 검색'),
          ),
        ),
      ),
    );
  }
}
