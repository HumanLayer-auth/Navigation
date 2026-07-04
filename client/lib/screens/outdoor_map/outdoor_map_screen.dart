import 'package:flutter/material.dart';

import '../../routing/app_routes.dart';

class OutdoorMapScreen extends StatelessWidget {
  const OutdoorMapScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('야외 지도 (GPS 모드)')),
      body: const Center(child: Text('flutter_map 연동 예정')),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: FilledButton(
            onPressed: () {
              Navigator.of(context).pushNamed(AppRoutes.indoorMap);
            },
            child: const Text('건물 진입 감지 (임시)'),
          ),
        ),
      ),
    );
  }
}
