import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:indoor_pdr_core/indoor_pdr_core.dart';

import '../application/indoor_navigation_controller.dart';
import '../contract/pdr_runtime_status.dart';
import '../platform/pdr_motion_source.dart';

const pdrDeviceHarnessReceiptName = 'pdr-device-harness-result.json';

Future<void> writePdrDeviceHarnessReceipt(String contents) async {
  final file = File(
    '${Directory.systemTemp.path}/$pdrDeviceHarnessReceiptName',
  );
  await file.writeAsString(contents, flush: true);
}

/// 제품 화면과 분리된 iOS 실기기 PDR acceptance 하니스.
class PdrDeviceHarness extends StatefulWidget {
  const PdrDeviceHarness({
    required this.source,
    required this.driver,
    this.walkingTimeout = const Duration(seconds: 45),
    this.stopObservation = const Duration(seconds: 2),
    this.writeReceipt = writePdrDeviceHarnessReceipt,
    super.key,
  });

  final PdrMotionSource source;
  final IndoorNavigationDriver driver;
  final Duration walkingTimeout;
  final Duration stopObservation;
  final Future<void> Function(String contents) writeReceipt;

  @override
  State<PdrDeviceHarness> createState() => _PdrDeviceHarnessState();
}

class _PdrDeviceHarnessState extends State<PdrDeviceHarness> {
  StreamSubscription<PdrRuntimeStatus>? _runtimeSub;
  StreamSubscription<PdrSnapshot>? _snapshotSub;
  Timer? _walkingTimer;

  PdrRuntimeStatus _runtimeStatus = const PdrRuntimeStatus.idle();
  String _headline = '센서 연결 중';
  String _detail = '아이폰의 Motion 센서를 시작하고 있습니다.';
  int _steps = 0;
  double _distanceM = 0;
  bool _verifyingStop = false;
  bool _completed = false;

  @override
  void initState() {
    super.initState();
    _runtimeSub = widget.driver.runtimeStatuses.listen(_onRuntimeStatus);
    _snapshotSub = widget.driver.snapshots.listen(_onSnapshot);
    unawaited(_writeReceipt('RUNNING', '센서 연결을 시작합니다.'));
    unawaited(widget.driver.startGuidance(floorId: 'device-smoke-floor'));
  }

  void _onRuntimeStatus(PdrRuntimeStatus status) {
    if (!mounted) return;
    setState(() => _runtimeStatus = status);
    if (_completed || _verifyingStop) return;
    if (status.state == PdrRuntimeState.running && _walkingTimer == null) {
      _walkingTimer = Timer(widget.walkingTimeout, () {
        _finish(
          passed: false,
          detail:
              '${widget.walkingTimeout.inSeconds}초 안에 걸음 snapshot을 받지 못했습니다.',
        );
      });
      setState(() {
        _headline = '걸어주세요';
        _detail = '20초 동안 자연스럽게 걸으면 자동으로 결과를 판정합니다.';
      });
      _log('WALK_NOW');
    } else if (status.state == PdrRuntimeState.degraded) {
      _finish(passed: false, detail: '센서 오류: ${status.warnings.join(', ')}');
    }
  }

  void _onSnapshot(PdrSnapshot snapshot) {
    if (!mounted) return;
    setState(() {
      _steps = snapshot.steps;
      _distanceM = snapshot.distanceM;
    });
    final moved =
        snapshot.position.eastM.abs() + snapshot.position.northM.abs() > 0;
    if (!_completed &&
        !_verifyingStop &&
        snapshot.steps > 0 &&
        snapshot.distanceM > 0 &&
        moved) {
      unawaited(_verifyStop());
    }
  }

  Future<void> _verifyStop() async {
    _verifyingStop = true;
    _walkingTimer?.cancel();
    if (mounted) {
      setState(() {
        _headline = '정지 확인 중';
        _detail = '센서 stop 이후 이벤트가 중단되는지 확인합니다.';
      });
    }

    var eventsAfterStop = 0;
    final eventSub = widget.source.events.listen((_) => eventsAfterStop++);
    try {
      await widget.driver.stopGuidance();
      eventsAfterStop = 0;
      await Future<void>.delayed(widget.stopObservation);
      _finish(
        passed: eventsAfterStop == 0,
        detail: eventsAfterStop == 0
            ? 'heading, 보행 snapshot, 센서 stop 검증을 모두 통과했습니다.'
            : 'stop 이후 native 이벤트가 $eventsAfterStop건 더 수신됐습니다.',
      );
    } on Object catch (error) {
      _finish(passed: false, detail: '센서 stop 확인 실패: $error');
    } finally {
      await eventSub.cancel();
    }
  }

  void _finish({required bool passed, required String detail}) {
    if (_completed || !mounted) return;
    _completed = true;
    _walkingTimer?.cancel();
    setState(() {
      _headline = passed ? 'PASS' : 'FAIL';
      _detail = detail;
    });
    _log(
      '${passed ? 'PASS' : 'FAIL'} steps=$_steps '
      'distanceM=${_distanceM.toStringAsFixed(2)} detail=$detail',
    );
    unawaited(_writeReceipt(passed ? 'PASS' : 'FAIL', detail));
    if (!passed) {
      unawaited(widget.driver.stopGuidance());
    }
  }

  void _log(String message) {
    // profile 실기기 실행에서 devicectl console이 수집하는 acceptance 증거.
    // ignore: avoid_print
    print('PDR_DEVICE_HARNESS_RESULT: $message');
  }

  Future<void> _writeReceipt(String result, String detail) {
    return widget.writeReceipt(
      jsonEncode({
        'result': result,
        'steps': _steps,
        'distanceM': _distanceM,
        'runtimeState': _runtimeStatus.state.name,
        'warnings': _runtimeStatus.warnings,
        'detail': detail,
        'recordedAt': DateTime.now().toUtc().toIso8601String(),
      }),
    );
  }

  @override
  void dispose() {
    _walkingTimer?.cancel();
    unawaited(_runtimeSub?.cancel());
    unawaited(_snapshotSub?.cancel());
    unawaited(widget.driver.dispose());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final passed = _headline == 'PASS';
    final failed = _headline == 'FAIL';
    final color = passed
        ? Colors.green
        : failed
        ? Colors.red
        : Theme.of(context).colorScheme.primary;
    return Scaffold(
      appBar: AppBar(title: const Text('PDR Device Smoke')),
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  passed
                      ? Icons.check_circle
                      : failed
                      ? Icons.cancel
                      : Icons.directions_walk,
                  color: color,
                  size: 72,
                ),
                const SizedBox(height: 20),
                Text(
                  _headline,
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    color: color,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 12),
                Text(_detail, textAlign: TextAlign.center),
                const SizedBox(height: 28),
                Text('runtime: ${_runtimeStatus.state.name}'),
                Text('$_steps걸음 · ${_distanceM.toStringAsFixed(2)}m'),
                if (_runtimeStatus.warnings.isNotEmpty)
                  Text('warnings: ${_runtimeStatus.warnings.join(', ')}'),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
