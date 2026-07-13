import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';

import '../theme/app_theme.dart';

/// 길찾기 시트에서 고를 수 있는 도착지 후보. 야외 모드에서는 [Building],
/// 실내 모드에서는 [PoiSearchResult]를 이 공통 형태로 변환해 검색·선택
/// 로직을 하나의 시트 위젯으로 공유한다.
class DirectionsCandidate {
  const DirectionsCandidate({
    required this.title,
    required this.subtitle,
    required this.point,
    this.nodeId,
    this.floor,
  });

  final String title;
  final String subtitle;
  final LatLng point;

  /// 실내 경로탐색(다익스트라)에 필요한 노드 ID. 야외 후보에는 없다.
  final String? nodeId;

  /// 실내 후보가 속한 층. 야외 후보에는 없다.
  final String? floor;
}

/// "현위치 → 도착지" 입력 바텀시트. 도착지에 타이핑하면 [search]로 후보를
/// 조회해 목록을 보여주고, 하나를 고르면 그 후보를 반환하며 닫힌다.
class DirectionsSheet extends StatefulWidget {
  const DirectionsSheet({
    super.key,
    required this.originLabel,
    required this.search,
  });

  final String originLabel;
  final Future<List<DirectionsCandidate>> Function(String query) search;

  static Future<DirectionsCandidate?> show(
    BuildContext context, {
    required String originLabel,
    required Future<List<DirectionsCandidate>> Function(String query) search,
  }) {
    return showModalBottomSheet<DirectionsCandidate>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (context) => DirectionsSheet(originLabel: originLabel, search: search),
    );
  }

  @override
  State<DirectionsSheet> createState() => _DirectionsSheetState();
}

class _DirectionsSheetState extends State<DirectionsSheet> {
  final _controller = TextEditingController();
  List<DirectionsCandidate> _results = [];
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _search('');
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _search(String query) async {
    setState(() => _loading = true);
    final results = await widget.search(query);
    if (!mounted) return;
    setState(() {
      _results = results;
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: DraggableScrollableSheet(
        initialChildSize: 0.6,
        minChildSize: 0.4,
        maxChildSize: 0.9,
        expand: false,
        builder: (context, scrollController) {
          return Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      '길찾기',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: AppColors.text),
                    ),
                    const SizedBox(height: 14),
                    _OriginRow(label: widget.originLabel),
                    const SizedBox(height: 8),
                    TextField(
                      controller: _controller,
                      autofocus: true,
                      onChanged: _search,
                      decoration: const InputDecoration(
                        prefixIcon: Icon(Icons.place_outlined, size: 20, color: AppColors.dest),
                        hintText: '도착지를 입력하세요',
                      ),
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              Expanded(
                child: _loading
                    ? const Center(child: CircularProgressIndicator())
                    : _results.isEmpty
                        ? const Center(
                            child: Text('검색 결과가 없습니다', style: TextStyle(color: AppColors.muted)),
                          )
                        : ListView.separated(
                            controller: scrollController,
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            itemCount: _results.length,
                            separatorBuilder: (_, _) => const Divider(height: 1),
                            itemBuilder: (context, index) {
                              final candidate = _results[index];
                              return ListTile(
                                leading: const Icon(Icons.place, color: AppColors.primary),
                                title: Text(
                                  candidate.title,
                                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                                ),
                                subtitle: Text(candidate.subtitle),
                                onTap: () => Navigator.of(context).pop(candidate),
                              );
                            },
                          ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _OriginRow extends StatelessWidget {
  const _OriginRow({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
      decoration: BoxDecoration(
        color: const Color(0xFFF3F4F6),
        borderRadius: BorderRadius.circular(26),
      ),
      child: Row(
        children: [
          const Icon(Icons.my_location, size: 18, color: AppColors.primary),
          const SizedBox(width: 10),
          Text(label, style: const TextStyle(fontSize: 14, color: AppColors.text)),
        ],
      ),
    );
  }
}
