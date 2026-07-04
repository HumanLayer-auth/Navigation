import 'package:flutter/material.dart';

import '../../routing/app_routes.dart';

class RouteGuideScreen extends StatelessWidget {
  const RouteGuideScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('경로 안내')),
      body: const Center(child: Text('경로 오버레이 / ETA 카드 예정')),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: FilledButton(
            onPressed: () {
              Navigator.of(context).pushNamed(AppRoutes.arrival);
            },
            child: const Text('도착'),
          ),
        ),
      ),
    );
  }
}
