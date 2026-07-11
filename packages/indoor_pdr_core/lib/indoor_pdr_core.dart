/// indoor_pdr_core — 실내 PDR 순수 Dart 코어의 공개 barrel.
///
/// typed 센서 이벤트(HeadingEvent/PedometerBatchEvent/AccelPeakEvent)를 받아
/// confirmed(초록)/preview(주황) 경로와 품질 신호를 계산한다. Flutter/플랫폼 채널/
/// 지도/GPS/JSON export에 의존하지 않는다.
library;

// domain
export 'src/domain/pdr_local_point.dart';
export 'src/domain/angle_utils.dart';
export 'src/domain/heading_sample.dart';
export 'src/domain/events.dart';
export 'src/domain/quality.dart';
export 'src/domain/snapshot.dart';
