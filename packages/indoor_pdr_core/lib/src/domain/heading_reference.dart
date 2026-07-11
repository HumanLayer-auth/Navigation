/// PDR heading이 어느 기준 frame인지.
///
/// iOS는 `.xMagneticNorthZVertical`을 우선 쓰되 미가용 시
/// `.xArbitraryCorrectedZVertical`로 fallback한다. 후자는 yaw가 자북 기준이 아니라
/// 서버의 자북 정렬각을 적용하면 안 되고 수동 방향 보정이 필요하다(§4).
enum HeadingReference { magneticNorth, arbitraryCorrected }

/// native headingSource 문자열에서 reference를 판별한다.
HeadingReference headingReferenceFromSource(String? source) {
  if (source != null && source.contains('xMagneticNorthZVertical')) {
    return HeadingReference.magneticNorth;
  }
  if (source != null && source.contains('xArbitraryCorrectedZVertical')) {
    return HeadingReference.arbitraryCorrected;
  }
  // 아직 heading을 못 받았거나 알 수 없으면 보수적으로 자북으로 가정하지 않는다.
  return HeadingReference.arbitraryCorrected;
}
