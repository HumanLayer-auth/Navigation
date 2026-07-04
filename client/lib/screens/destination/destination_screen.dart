import 'package:flutter/material.dart';

import '../../routing/app_routes.dart';

class DestinationScreen extends StatelessWidget {
  const DestinationScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('목적지 입력')),
      body: const Center(child: Text('자연어 / POI 목록 검색 예정')),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: FilledButton(
            onPressed: () {
              Navigator.of(context).pushNamed(AppRoutes.routeGuide);
            },
            child: const Text('경로 시작'),
          ),
        ),
      ),
    );
  }
}
