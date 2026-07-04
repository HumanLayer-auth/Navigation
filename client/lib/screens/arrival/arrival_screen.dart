import 'package:flutter/material.dart';

import '../../routing/app_routes.dart';

class ArrivalScreen extends StatelessWidget {
  const ArrivalScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.check_circle, color: Colors.green, size: 64),
            const SizedBox(height: 16),
            const Text('도착했습니다!'),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: () {
                Navigator.of(
                  context,
                ).pushNamedAndRemoveUntil(AppRoutes.indoorMap, (route) => route.isFirst);
              },
              child: const Text('새 목적지 탐색'),
            ),
          ],
        ),
      ),
    );
  }
}
