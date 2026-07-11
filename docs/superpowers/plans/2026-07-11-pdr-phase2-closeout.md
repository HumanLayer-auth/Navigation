# PDR Phase 2 Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** iOS PDR 센서 파이프라인을 앱 범위 DI와 lifecycle에 연결하고, runtime 오류 상태와 실기기 headless smoke test를 추가해 Phase 2 완료 조건을 검증한다.

**Architecture:** Pure Dart `indoor_pdr_core`는 변경하지 않고, client의 headless controller가 플랫폼 센서 상태를 소유한다. 안정된 `PdrRuntimeStatus` 계약으로 시작·실행·일시정지·오류 상태를 UI에 노출하고, 앱 루트는 lifecycle만 전달한다. 실제 iPhone 검증은 제품 화면을 추가하지 않는 opt-in integration test로 수행한다.

**Tech Stack:** Dart 3.12, Flutter, `flutter_test`, `integration_test`, iOS EventChannel/MethodChannel, CoreMotion, CMPedometer

## Global Constraints

- 설명·주석·커밋 메시지는 한국어, 코드와 식별자는 영어로 작성한다.
- `.local/indoor-sensor-navigation-mock/app`은 읽기 전용이며 import하지 않는다.
- `indoor_pdr_core`의 Flutter SDK 의존성은 0으로 유지한다.
- 제품 위젯·지도 렌더러·Phase 3 `local_m`/anchor 정밀화는 구현하지 않는다.
- 기존 미추적 `api/tests/integration/test_buildings_api.py`, `client/integration_test/health_check_test.dart`, `client/lib/core/config/`, `client/lib/data/`, `client/lib/features/map/`, `client/lib/state/`, `tests/`는 수정·삭제·스테이지하지 않는다.
- 각 동작 변경은 failing test를 먼저 확인한 후 최소 구현으로 통과시킨다.
- Phase 2 완료 표시는 실제 iPhone smoke test까지 통과한 뒤에만 한다.

---

### Task 1: Runtime 상태 공개 계약

**Files:**
- Create: `client/lib/features/indoor_navigation/contract/pdr_runtime_status.dart`
- Modify: `client/lib/features/indoor_navigation/contract/indoor_navigation_intents.dart`
- Modify: `client/lib/features/indoor_navigation/contract/indoor_navigation_view.dart`
- Modify: `client/lib/features/indoor_navigation/contract/indoor_navigation_contract.dart`
- Modify: `client/test/features/indoor_navigation/contract_test.dart`

**Interfaces:**
- Produces: `PdrRuntimeState`, `PdrRuntimeStatus`, `runtimeStatuses`, `currentRuntimeStatus`
- Changes: `startGuidance`, `stopGuidance`, `changeFloor` return `Future<void>`

- [ ] **Step 1: Write the failing contract test**

Extend `FakeIndoorNavigation` with the wished-for runtime API and change its intents to async:

```dart
final _runtimeStatuses = StreamController<PdrRuntimeStatus>.broadcast();
PdrRuntimeStatus _runtimeStatus = const PdrRuntimeStatus.idle();

@override
Stream<PdrRuntimeStatus> get runtimeStatuses => _runtimeStatuses.stream;

@override
PdrRuntimeStatus get currentRuntimeStatus => _runtimeStatus;

@override
Future<void> startGuidance({required String floorId}) async {
  log.add('start:$floorId');
}

@override
Future<void> stopGuidance() async => log.add('stop');

@override
Future<void> changeFloor({required String floorId}) async {
  log.add('floor:$floorId');
}
```

Add assertions:

```dart
test('runtime 초기 상태는 idle이고 warning이 없다', () {
  final nav = FakeIndoorNavigation();
  expect(nav.currentRuntimeStatus.state, PdrRuntimeState.idle);
  expect(nav.currentRuntimeStatus.warnings, isEmpty);
  nav.dispose();
});
```

Await all three async intents in the existing forwarding test.

- [ ] **Step 2: Run the contract test and verify RED**

Run:

```bash
cd client
flutter test test/features/indoor_navigation/contract_test.dart
```

Expected: compile failure because `PdrRuntimeStatus`, `PdrRuntimeState`, and runtime view members do not exist.

- [ ] **Step 3: Implement the runtime contract**

Create `pdr_runtime_status.dart`:

```dart
enum PdrRuntimeState { idle, starting, running, paused, stopping, degraded }

class PdrRuntimeStatus {
  const PdrRuntimeStatus({required this.state, this.warnings = const []});
  const PdrRuntimeStatus.idle()
      : state = PdrRuntimeState.idle,
        warnings = const [];

  final PdrRuntimeState state;
  final List<String> warnings;
}
```

Add the two runtime getters to `IndoorNavigationView`, export the new file from the contract barrel, and change the three intent signatures to `Future<void>`. Update the fake `dispose()` to close `_runtimeStatuses`.

- [ ] **Step 4: Run the contract test and verify GREEN**

Run the same command. Expected: all contract tests pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add client/lib/features/indoor_navigation/contract client/test/features/indoor_navigation/contract_test.dart
git commit -m "feat(pdr): runtime 상태 계약 추가"
```

---

### Task 2: Controller runtime 오류와 quality 합성

**Files:**
- Modify: `client/lib/features/indoor_navigation/application/indoor_navigation_controller.dart`
- Modify: `client/test/features/indoor_navigation/controller_test.dart`

**Interfaces:**
- Consumes: Task 1 runtime contract
- Produces: async lifecycle methods `onAppBackgrounded()` and `onAppForegrounded()`
- Behavior: first event → running, platform error → degraded, degraded snapshot quality overlay

- [ ] **Step 1: Extend the fake source for deterministic failures**

Add fields and methods to `FakePdrMotionSource`:

```dart
Object? startError;
Object? stopError;
Object? resetError;

@override
Future<void> start() async {
  startCount++;
  if (startError case final error?) throw error;
}

@override
Future<void> stop() async {
  stopCount++;
  if (stopError case final error?) throw error;
}

@override
Future<int?> resetPedometer() async {
  resetCount++;
  if (resetError case final error?) throw error;
  return ++_sessionId;
}

void emitError(Object error) => _controller.addError(error);
```

- [ ] **Step 2: Write failing runtime transition tests**

Add separate tests for:

```dart
test('start는 starting이고 첫 native 이벤트 뒤 running이다', () async {
  await driver.startGuidance(floorId: 'F1');
  expect(driver.currentRuntimeStatus.state, PdrRuntimeState.starting);
  source.emitRaw(motionEvent(tMs: 1000));
  await settle();
  expect(driver.currentRuntimeStatus.state, PdrRuntimeState.running);
});

test('센서 시작 실패는 degraded warning으로 노출된다', () async {
  source.startError = StateError('denied');
  await driver.startGuidance(floorId: 'F1');
  expect(driver.currentRuntimeStatus.state, PdrRuntimeState.degraded);
  expect(driver.currentRuntimeStatus.warnings, contains('sensorStartFailed'));
});

test('센서 stream 오류는 처리되어 degraded가 된다', () async {
  await driver.startGuidance(floorId: 'F1');
  source.emitError(StateError('stream'));
  await settle();
  expect(driver.currentRuntimeStatus.state, PdrRuntimeState.degraded);
  expect(driver.currentRuntimeStatus.warnings, contains('sensorStreamError'));
});
```

- [ ] **Step 3: Run controller tests and verify RED**

```bash
cd client
flutter test test/features/indoor_navigation/controller_test.dart
```

Expected: compile failures for runtime members/async signatures or assertion failures because no runtime transitions exist.

- [ ] **Step 4: Implement runtime state and error capture**

In `IndoorNavigationDriver` add:

```dart
final _runtimeStatuses = StreamController<PdrRuntimeStatus>.broadcast();
PdrRuntimeStatus _runtimeStatus = const PdrRuntimeStatus.idle();
bool _backgrounded = false;

@override
Stream<PdrRuntimeStatus> get runtimeStatuses => _runtimeStatuses.stream;

@override
PdrRuntimeStatus get currentRuntimeStatus => _runtimeStatus;

void _updateRuntime(PdrRuntimeState state, {List<String> warnings = const []}) {
  _runtimeStatus = PdrRuntimeStatus(state: state, warnings: List.unmodifiable(warnings));
  if (!_runtimeStatuses.isClosed) _runtimeStatuses.add(_runtimeStatus);
}
```

Make `startGuidance`, `stopGuidance`, and `changeFloor` async. Subscribe with `onError: _onSourceError`. Set `starting` before source start; set `running` on the first native event. Catch start/reset failures and map them to stable warning codes. Add `_runtimeStatuses.close()` to `dispose()`.

첫 이벤트는 현재 상태가 `starting`일 때만 `running`으로 바꾼다. 이미 `degraded`인 상태는 이후
센서 이벤트가 도착해도 자동 복구하지 않아 warning과 quality overlay가 유실되지 않게 한다.

- [ ] **Step 5: Run controller tests and verify GREEN for transitions**

Run the same controller test command. Expected: transition/error tests and existing tests pass after adding required `await`s.

- [ ] **Step 6: Write failing degraded quality test**

```dart
test('runtime 오류 뒤 snapshot quality와 warning도 degraded로 합성된다', () async {
  await driver.startGuidance(floorId: 'F1');
  source.emitError(StateError('stream'));
  source.emitRaw(motionEvent(tMs: 1000));
  source.emitRaw(pedometerEvent(
    steps: 4,
    sessionStartMs: 900,
    endMs: 2000,
    distanceM: 2.8,
    peaks: [1200, 1600],
  ));
  await settle();
  expect(driver.currentSnapshot!.quality.state, PdrQualityState.degraded);
  expect(driver.currentSnapshot!.quality.warnings, contains('sensorStreamError'));
});
```

- [ ] **Step 7: Run the single test and verify RED**

Run the controller test file. Expected: snapshot quality does not contain `sensorStreamError`.

- [ ] **Step 8: Implement snapshot quality overlay**

Add a helper that returns the original snapshot unless runtime is degraded. In degraded state construct a new `PdrSnapshot` preserving all fields and replace only quality:

```dart
PdrSnapshot _withRuntimeQuality(PdrSnapshot snapshot) {
  if (_runtimeStatus.state != PdrRuntimeState.degraded) return snapshot;
  final warnings = <String>{
    ...snapshot.quality.warnings,
    ..._runtimeStatus.warnings,
  }.toList(growable: false);
  return PdrSnapshot(
    position: snapshot.position,
    path: snapshot.path,
    steps: snapshot.steps,
    distanceM: snapshot.distanceM,
    walkingHeadingDeg: snapshot.walkingHeadingDeg,
    hasHeading: snapshot.hasHeading,
    preview: snapshot.preview,
    quality: PdrQuality(
      state: PdrQualityState.degraded,
      warnings: warnings,
      features: snapshot.quality.features,
    ),
  );
}
```

Use the helper before assigning `_current` and emitting snapshots.

- [ ] **Step 9: Run controller and contract tests**

```bash
flutter test test/features/indoor_navigation/contract_test.dart test/features/indoor_navigation/controller_test.dart
```

Expected: all pass.

- [ ] **Step 10: Commit Task 2**

```bash
git add client/lib/features/indoor_navigation/application/indoor_navigation_controller.dart client/test/features/indoor_navigation/controller_test.dart
git commit -m "feat(pdr): 센서 runtime 오류와 품질 상태 연결"
```

---

### Task 3: Background/foreground 센서 lifecycle

**Files:**
- Modify: `client/lib/features/indoor_navigation/application/indoor_navigation_controller.dart`
- Modify: `client/test/features/indoor_navigation/controller_test.dart`

**Interfaces:**
- Consumes: `PdrMotionSource.start/stop`
- Produces: `Future<void> onAppBackgrounded()`, `Future<void> onAppForegrounded()`

- [ ] **Step 1: Write failing lifecycle tests**

Add tests that await lifecycle calls and assert:

```dart
test('안내 중 background는 tracking과 native source를 한 번 멈춘다', () async {
  await driver.startGuidance(floorId: 'F1');
  source.emitRaw(motionEvent(tMs: 1000));
  await settle();
  await driver.onAppBackgrounded();
  await driver.onAppBackgrounded();
  expect(source.stopCount, 1);
  expect(driver.currentRuntimeStatus.state, PdrRuntimeState.paused);
});

test('background 뒤 foreground는 source와 tracking을 한 번 재개한다', () async {
  await driver.startGuidance(floorId: 'F1');
  await driver.onAppBackgrounded();
  await driver.onAppForegrounded();
  await driver.onAppForegrounded();
  expect(source.startCount, 2);
  expect(driver.currentRuntimeStatus.state, PdrRuntimeState.starting);
});

test('안내 중이 아니면 lifecycle이 source를 호출하지 않는다', () async {
  await driver.onAppBackgrounded();
  await driver.onAppForegrounded();
  expect(source.startCount, 0);
  expect(source.stopCount, 0);
});
```

- [ ] **Step 2: Run controller tests and verify RED**

Expected: current methods are synchronous, do not stop/restart source, and are not idempotent.

- [ ] **Step 3: Implement idempotent lifecycle**

Make both methods async. Guard with `_guiding` and `_backgrounded`. Background pauses at the latest motion timestamp, awaits `_source.stop()`, and sets paused. Foreground awaits `_source.start()`, resumes the timeline, clears `_backgrounded`, and sets starting. Map resume failure to `sensorResumeFailed` and degraded.

- [ ] **Step 4: Run all controller tests and verify GREEN**

```bash
flutter test test/features/indoor_navigation/controller_test.dart
```

- [ ] **Step 5: Commit Task 3**

```bash
git add client/lib/features/indoor_navigation/application/indoor_navigation_controller.dart client/test/features/indoor_navigation/controller_test.dart
git commit -m "feat(pdr): 앱 lifecycle에 센서 pause resume 연결"
```

---

### Task 4: 앱 범위 DI와 root lifecycle observer

**Files:**
- Modify: `client/lib/core/service_locator.dart`
- Modify: `client/lib/app.dart`
- Create: `client/test/features/indoor_navigation/app_lifecycle_test.dart`

**Interfaces:**
- Produces: app singleton `pdrMotionSource`, `indoorNavigationDriver`
- Produces: testable `NavigationApp(onPdrBackgrounded:, onPdrForegrounded:)`

- [ ] **Step 1: Write failing app lifecycle widget test**

Create a test that pumps callbacks without touching platform channels:

```dart
testWidgets('앱 lifecycle을 PDR callback으로 전달한다', (tester) async {
  var backgrounds = 0;
  var foregrounds = 0;
  await tester.pumpWidget(NavigationApp(
    onPdrBackgrounded: () => backgrounds++,
    onPdrForegrounded: () => foregrounds++,
  ));
  tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
  await tester.pump();
  tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
  await tester.pump();
  expect(backgrounds, 1);
  expect(foregrounds, 1);
});
```

- [ ] **Step 2: Run the widget test and verify RED**

```bash
cd client
flutter test test/features/indoor_navigation/app_lifecycle_test.dart
```

Expected: `NavigationApp` has no lifecycle callback constructor parameters.

- [ ] **Step 3: Add app-scoped PDR dependencies**

In `service_locator.dart`, import the controller and iOS source and add:

```dart
final PdrMotionSource pdrMotionSource = IosPdrMotionSource();
final IndoorNavigationDriver indoorNavigationDriver =
    IndoorNavigationDriver(source: pdrMotionSource);
```

- [ ] **Step 4: Implement the root lifecycle observer**

Convert `NavigationApp` to a `StatefulWidget` with optional `VoidCallback` injections. Production defaults call `unawaited(indoorNavigationDriver.onAppBackgrounded())` and foreground equivalent. Register/unregister `WidgetsBindingObserver` in `initState`/`dispose`, and map resumed versus all non-resumed active-loss states without duplicate callbacks for repeated identical states.

- [ ] **Step 5: Run widget and existing app tests**

```bash
flutter test test/features/indoor_navigation/app_lifecycle_test.dart
flutter test
```

Expected: lifecycle test and existing tests pass.

- [ ] **Step 6: Commit Task 4**

```bash
git add client/lib/core/service_locator.dart client/lib/app.dart client/test/features/indoor_navigation/app_lifecycle_test.dart
git commit -m "feat(pdr): 앱 범위 DI와 lifecycle 연결"
```

---

### Task 5: 실제 iPhone headless smoke harness

**Files:**
- Create: `client/integration_test/pdr_device_smoke_test.dart`

**Interfaces:**
- Consumes: `IosPdrMotionSource`, `IndoorNavigationDriver`, runtime status and snapshot streams
- Enabled by: `--dart-define=PDR_DEVICE_SMOKE=true`

- [ ] **Step 1: Add an opt-in integration test harness**

Create a test with `IntegrationTestWidgetsFlutterBinding.ensureInitialized()`. When `PDR_DEVICE_SMOKE` is false, mark it skipped. When enabled:

```dart
const enabled = bool.fromEnvironment('PDR_DEVICE_SMOKE');

testWidgets(
  'iOS 실기기 센서가 PDR snapshot을 갱신하고 stop 후 멈춘다',
  (tester) async {
    final source = IosPdrMotionSource();
    final driver = IndoorNavigationDriver(source: source);
    addTearDown(driver.dispose);

    await driver.startGuidance(floorId: 'device-smoke-floor');
    await driver.runtimeStatuses
        .firstWhere((s) => s.state == PdrRuntimeState.running)
        .timeout(const Duration(seconds: 15));

    // ignore: avoid_print
    print('PDR_DEVICE_SMOKE_WALK_NOW: 20초 동안 자연스럽게 걸어주세요.');
    final snapshot = await driver.snapshots
        .firstWhere((s) => s.steps > 0 && s.distanceM > 0)
        .timeout(const Duration(seconds: 45));
    expect(
      snapshot.position.eastM.abs() + snapshot.position.northM.abs(),
      greaterThan(0),
    );

    var eventsAfterStop = 0;
    final sub = source.events.listen((_) => eventsAfterStop++);
    await driver.stopGuidance();
    eventsAfterStop = 0;
    await Future<void>.delayed(const Duration(seconds: 2));
    expect(eventsAfterStop, 0);
    await sub.cancel();
  },
  skip: !enabled,
);
```

- [ ] **Step 2: Verify the harness is skipped by default**

```bash
cd client
flutter test integration_test/pdr_device_smoke_test.dart
```

Expected: one skipped test, no platform channel invocation.

- [ ] **Step 3: Analyze the harness and PDR paths**

```bash
flutter analyze lib/app.dart lib/core/service_locator.dart lib/features/indoor_navigation test/features/indoor_navigation integration_test/pdr_device_smoke_test.dart
```

Expected: no issues.

- [ ] **Step 4: Commit Task 5**

```bash
git add client/integration_test/pdr_device_smoke_test.dart
git commit -m "test(pdr): iOS 실기기 headless smoke 하니스 추가"
```

---

### Task 6: 문서 정합성과 자동 검증

**Files:**
- Modify: `docs/pdr-ui-contract.md`
- Modify: `docs/pdr-migration-plan.md`

**Interfaces:**
- Documents: async intents, runtime status, Phase 2 evidence and remaining physical-device gate

- [ ] **Step 1: Update the UI contract document**

Document `runtimeStatuses`, `currentRuntimeStatus`, state meanings, warning codes, and that start/stop/changeFloor must be awaited. Preserve the rule that uncalibrated positions are not rendered.

- [ ] **Step 2: Update Phase 2 status without overstating completion**

Add an evidence subsection to the migration plan listing unit tests, scoped analyze, simulator build, and device smoke result. Mark Phase 2 complete only after Task 7 succeeds.

- [ ] **Step 3: Run fresh automatic verification**

```bash
cd packages/indoor_pdr_core
dart test
dart analyze

cd ../../client
flutter test
flutter analyze lib/app.dart lib/core/service_locator.dart lib/features/indoor_navigation test/features/indoor_navigation integration_test/pdr_device_smoke_test.dart
flutter build ios --simulator --debug
```

Expected: all commands exit 0; the opt-in device test is skipped during normal `flutter test`.

- [ ] **Step 4: Record the unrelated full-analyze baseline**

```bash
flutter analyze
```

Expected current baseline: failures only in pre-existing untracked `health_check_test.dart`, `data/`, `features/map/`, and `state/` files. Confirm no new issue points to Phase 2 files.

- [ ] **Step 5: Commit documentation before device run**

```bash
git add docs/pdr-ui-contract.md docs/pdr-migration-plan.md
git commit -m "docs: PDR Phase 2 runtime 계약과 검증 절차 반영"
```

---

### Task 7: Connected iPhone acceptance

**Files:**
- Modify only if successful: `docs/pdr-migration-plan.md`

**Interfaces:**
- Device: `00008110-001944D22E05801E` (`아이폰십삼프로`)
- Requires: unlocked device, trusted developer, Motion permission, user walking during the 45-second window

- [ ] **Step 1: Confirm the connected device**

```bash
cd client
flutter devices
```

Expected: device id `00008110-001944D22E05801E` is listed as an iOS device.

- [ ] **Step 2: Start the opt-in smoke test and prompt the user to walk**

```bash
flutter test integration_test/pdr_device_smoke_test.dart \
  -d 00008110-001944D22E05801E \
  --dart-define=PDR_DEVICE_SMOKE=true
```

Tell the user immediately when the command reaches installation/run that they should unlock the phone, approve Motion permission if prompted, and walk naturally for 20 seconds.

Expected: heading arrives within 15 seconds, a positive-step snapshot arrives within 45 seconds, and no event arrives during the two seconds after stop.

- [ ] **Step 3: If the device test fails, preserve truthful status**

Classify the failure as signing/install, permission, no heading, no walking snapshot, or stop leak. Fix code failures through a new failing unit/integration test. If user/device interaction blocks the run, do not mark Phase 2 complete and record the exact external blocker.

- [ ] **Step 4: If the device test passes, mark Phase 2 complete**

Add the command, device identifier/name, date, and observed pass result to the Phase 2 evidence subsection. Do not include personal device metadata beyond the existing display name and identifier already used by the local toolchain.

- [ ] **Step 5: Run final verification after the documentation change**

Repeat Task 6 Step 3 and run `git diff --check` plus `git status --short`. Confirm unrelated untracked files remain untouched.

- [ ] **Step 6: Commit the acceptance evidence**

```bash
git add docs/pdr-migration-plan.md
git commit -m "docs: PDR Phase 2 실기기 검증 완료"
```
