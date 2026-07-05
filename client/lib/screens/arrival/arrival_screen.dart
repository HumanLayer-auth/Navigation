import 'dart:async';

import 'package:flutter/material.dart';

import '../../models/poi_search_result.dart';
import '../../routing/app_routes.dart';

const _autoDismissDelay = Duration(seconds: 2);

class ArrivalScreen extends StatefulWidget {
  const ArrivalScreen({super.key});

  @override
  State<ArrivalScreen> createState() => _ArrivalScreenState();
}

class _ArrivalScreenState extends State<ArrivalScreen> {
  Timer? _autoDismissTimer;

  @override
  void initState() {
    super.initState();
    _autoDismissTimer = Timer(_autoDismissDelay, _startNewSearch);
  }

  @override
  void dispose() {
    _autoDismissTimer?.cancel();
    super.dispose();
  }

  void _startNewSearch() {
    _autoDismissTimer?.cancel();
    if (!mounted) return;
    Navigator.of(
      context,
    ).pushNamedAndRemoveUntil(AppRoutes.indoorMap, (route) => route.isFirst);
  }

  @override
  Widget build(BuildContext context) {
    final destination =
        ModalRoute.of(context)?.settings.arguments as PoiSearchResult?;

    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.check_circle, color: Colors.green, size: 64),
            const SizedBox(height: 16),
            Text(
              destination == null
                  ? '도착했습니다!'
                  : '${destination.name}에 도착했습니다!',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _startNewSearch,
              child: const Text('새 목적지 탐색'),
            ),
          ],
        ),
      ),
    );
  }
}
