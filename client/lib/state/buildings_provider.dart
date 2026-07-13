import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/building.dart';
import '../data/repositories/building_repository.dart';

final buildingRepositoryProvider = Provider<BuildingRepository>((ref) {
  return BuildingRepository();
});

final buildingsProvider = FutureProvider.autoDispose<List<Building>>((ref) {
  return ref.watch(buildingRepositoryProvider).fetchBuildings();
});
