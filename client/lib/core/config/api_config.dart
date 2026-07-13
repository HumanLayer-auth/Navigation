import 'package:flutter/foundation.dart';

class ApiConfig {
  const ApiConfig({required this.baseUrl});

  static const _configuredBaseUrl = String.fromEnvironment('API_BASE_URL');

  static ApiConfig get current {
    if (_configuredBaseUrl.isNotEmpty) {
      return const ApiConfig(baseUrl: _configuredBaseUrl);
    }

    return ApiConfig(baseUrl: _defaultBaseUrl());
  }

  final String baseUrl;

  static String _defaultBaseUrl() {
    if (kIsWeb) {
      return 'http://localhost:8000';
    }

    return switch (defaultTargetPlatform) {
      TargetPlatform.android => 'http://10.0.2.2:8000',
      TargetPlatform.iOS => 'http://localhost:8000',
      TargetPlatform.macOS ||
      TargetPlatform.linux ||
      TargetPlatform.windows ||
      TargetPlatform.fuchsia => 'http://localhost:8000',
    };
  }
}
