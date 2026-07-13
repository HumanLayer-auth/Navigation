import 'package:dio/dio.dart';

import '../../core/config/api_config.dart';
import '../models/building.dart';

class BuildingRepository {
  BuildingRepository({Dio? dio, ApiConfig? config})
    : _dio =
          dio ??
          Dio(
            BaseOptions(
              baseUrl: (config ?? ApiConfig.current).baseUrl,
              connectTimeout: const Duration(seconds: 3),
              receiveTimeout: const Duration(seconds: 3),
            ),
          );

  final Dio _dio;

  Future<List<Building>> fetchBuildings() async {
    try {
      final response = await _dio.get<List<dynamic>>('/buildings');
      final data = response.data;
      if (data == null) {
        throw const FormatException('Building response was empty.');
      }

      return data
          .map((item) => Building.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (error) {
      throw BuildingRepositoryException('서버에 연결할 수 없음', cause: error);
    } on FormatException catch (error) {
      throw BuildingRepositoryException('건물 데이터를 읽을 수 없음', cause: error);
    }
  }
}

class BuildingRepositoryException implements Exception {
  const BuildingRepositoryException(this.message, {this.cause});

  final String message;
  final Object? cause;

  @override
  String toString() => message;
}
