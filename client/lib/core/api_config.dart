const apiBaseUrl = 'http://10.0.2.2:8001';

/// 데모 데이터셋의 유일한 건물 ID. 다건물 지원은 범위 밖(design.md 8번 항목).
const demoBuildingId = 'bldg-001';

/// TMAP(SK Open API) 보행자 경로 안내. https://openapi.sk.com 에서 앱 등록 후 발급.
/// 키를 소스코드에 직접 적지 않고 실행 시점에 주입한다:
///   flutter run --dart-define=TMAP_APP_KEY=발급받은키
/// 값을 안 넘기면 빈 문자열이 되고, service_locator.dart가 이 경우 자동으로
/// MockDirectionsRepository를 사용한다.
const tmapAppKey = String.fromEnvironment('TMAP_APP_KEY');
const tmapBaseUrl = 'https://apis.openapi.sk.com/tmap';
