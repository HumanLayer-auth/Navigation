import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/building.dart';
import '../../state/buildings_provider.dart';

class MapScreen extends ConsumerWidget {
  const MapScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final buildings = ref.watch(buildingsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Navigation')),
      body: buildings.when(
        data: (items) => _BuildingList(buildings: items),
        error: (error, stackTrace) => _BuildingError(
          message: error.toString(),
          onRetry: () => ref.invalidate(buildingsProvider),
        ),
        loading: () => const Center(
          child: CircularProgressIndicator(key: Key('buildings-loading')),
        ),
      ),
    );
  }
}

class _BuildingList extends StatelessWidget {
  const _BuildingList({required this.buildings});

  final List<Building> buildings;

  @override
  Widget build(BuildContext context) {
    if (buildings.isEmpty) {
      return const Center(child: Text('표시할 건물이 없습니다'));
    }

    return ListView.separated(
      key: const Key('buildings-list'),
      padding: const EdgeInsets.all(16),
      itemCount: buildings.length,
      separatorBuilder: (context, index) => const Divider(height: 1),
      itemBuilder: (context, index) {
        final building = buildings[index];
        return ListTile(
          key: Key('building-${building.id}'),
          title: Text(building.name),
          subtitle: Text('층: ${building.floors.join(', ')}'),
          leading: const Icon(Icons.location_city_outlined),
        );
      },
    );
  }
}

class _BuildingError extends StatelessWidget {
  const _BuildingError({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_outlined, size: 40),
            const SizedBox(height: 12),
            Text(
              message.contains('서버에 연결할 수 없음') ? '서버에 연결할 수 없음' : message,
              key: const Key('buildings-error'),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('다시 시도'),
            ),
          ],
        ),
      ),
    );
  }
}
