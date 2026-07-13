import 'package:flutter/material.dart';

/// design.md 4장 컬러 시스템 토큰.
class AppColors {
  AppColors._();

  static const background = Color(0xFFF6F5F1);
  static const surface = Color(0xFFFFFFFF);
  static const surfaceSubtle = Color(0xFFF1F0EC);

  static const primary = Color(0xFF0F5C5E);
  static const primaryDark = Color(0xFF0B4749);
  static const primarySoft = Color(0xFFDCE9E7);

  static const destination = Color(0xFFFF6B4A);
  static const destinationSoft = Color(0xFFFDE5DE);

  static const textPrimary = Color(0xFF1D2222);
  static const textSecondary = Color(0xFF646B69);
  static const textTertiary = Color(0xFF969C99);

  static const border = Color(0xFFDDDFDB);
  static const divider = Color(0xFFE8E9E5);

  static const mapWall = Color(0xFFB8BCB8);
  static const mapWallStrong = Color(0xFF8F9692);
  static const mapFloor = Color(0xFFFAF9F6);
  static const mapBlock = Color(0xFFEEEDE8);
  static const iconDefault = Color(0xFF7B817E);

  static const success = Color(0xFF2D7A61);
  static const warning = Color(0xFFC78A2C);
  static const error = Color(0xFFC94A43);
  static const info = Color(0xFF54758E);
}

/// design.md 6.1 기본 그리드.
class AppSpacing {
  AppSpacing._();

  static const double xxs = 4;
  static const double xs = 8;
  static const double sm = 12;
  static const double md = 16;
  static const double screen = 20;
  static const double lg = 24;
  static const double xl = 32;
}

/// design.md 6.2 Corner Radius.
class AppRadius {
  AppRadius._();

  static const double small = 8;
  static const double medium = 12;
  static const double large = 18;
  static const double sheet = 24;
}

/// design.md 6.3 Shadow — 지도 위 플로팅 버튼·하단 패널·검색창 전용.
const appShadow = [
  BoxShadow(color: Color(0x0F1A2322), offset: Offset(0, 4), blurRadius: 16),
];

/// design.md 5.2 Type Scale.
class AppTextStyles {
  AppTextStyles._();

  static const display = TextStyle(
    fontSize: 32,
    fontWeight: FontWeight.w700,
    height: 40 / 32,
    color: AppColors.textPrimary,
  );
  static const heading1 = TextStyle(
    fontSize: 24,
    fontWeight: FontWeight.w700,
    height: 32 / 24,
    color: AppColors.textPrimary,
  );
  static const heading2 = TextStyle(
    fontSize: 20,
    fontWeight: FontWeight.w700,
    height: 28 / 20,
    color: AppColors.textPrimary,
  );
  static const title = TextStyle(
    fontSize: 17,
    fontWeight: FontWeight.w600,
    height: 24 / 17,
    color: AppColors.textPrimary,
  );
  static const body = TextStyle(
    fontSize: 15,
    fontWeight: FontWeight.w400,
    height: 22 / 15,
    color: AppColors.textPrimary,
  );
  static const bodyStrong = TextStyle(
    fontSize: 15,
    fontWeight: FontWeight.w600,
    height: 22 / 15,
    color: AppColors.textPrimary,
  );
  static const label = TextStyle(
    fontSize: 13,
    fontWeight: FontWeight.w500,
    height: 18 / 13,
    color: AppColors.textSecondary,
  );
  static const caption = TextStyle(
    fontSize: 12,
    fontWeight: FontWeight.w400,
    height: 17 / 12,
    color: AppColors.textSecondary,
  );
  static const micro = TextStyle(
    fontSize: 11,
    fontWeight: FontWeight.w500,
    height: 15 / 11,
    color: AppColors.textSecondary,
  );
}

/// design.md 컨셉(Minimal Architectural Navigation)에 맞춘 라이트 테마.
/// Pretendard는 번들하지 않았으므로 설치된 경우에만 쓰고, 없으면 시스템
/// 한글 폰트(Apple SD Gothic Neo 등)로 자연스럽게 대체된다.
ThemeData buildAppTheme() {
  final colorScheme =
      ColorScheme.fromSeed(seedColor: AppColors.primary).copyWith(
        primary: AppColors.primary,
        onPrimary: Colors.white,
        secondary: AppColors.primaryDark,
        surface: AppColors.surface,
        onSurface: AppColors.textPrimary,
        error: AppColors.error,
        outline: AppColors.border,
        outlineVariant: AppColors.divider,
      );

  const fontFallback = ['Pretendard', 'SUIT', 'Apple SD Gothic Neo'];

  final base = ThemeData(
    useMaterial3: true,
    colorScheme: colorScheme,
    scaffoldBackgroundColor: AppColors.background,
    splashFactory: InkSparkle.splashFactory,
  );

  final textTheme = base.textTheme
      .apply(
        bodyColor: AppColors.textPrimary,
        displayColor: AppColors.textPrimary,
        fontFamilyFallback: fontFallback,
      )
      .copyWith(
        headlineSmall: AppTextStyles.heading1,
        titleLarge: AppTextStyles.heading2,
        titleMedium: AppTextStyles.title,
        bodyMedium: AppTextStyles.body,
        labelMedium: AppTextStyles.label,
        bodySmall: AppTextStyles.caption,
      );

  return base.copyWith(
    textTheme: textTheme,
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.background,
      foregroundColor: AppColors.textPrimary,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      titleTextStyle: AppTextStyles.heading2,
      iconTheme: IconThemeData(color: AppColors.textPrimary),
    ),
    filledButtonTheme: FilledButtonThemeData(
      // design.md 9.4 Primary Button: 52px, Deep Teal, radius 12.
      style: ButtonStyle(
        minimumSize: const WidgetStatePropertyAll(Size.fromHeight(52)),
        shape: WidgetStatePropertyAll(
          RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.medium),
          ),
        ),
        backgroundColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.disabled)) {
            return AppColors.textTertiary;
          }
          if (states.contains(WidgetState.pressed)) {
            return AppColors.primaryDark;
          }
          return AppColors.primary;
        }),
        foregroundColor: const WidgetStatePropertyAll(Colors.white),
        textStyle: const WidgetStatePropertyAll(
          TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(foregroundColor: AppColors.textSecondary),
    ),
    dividerTheme: const DividerThemeData(
      color: AppColors.divider,
      thickness: 1,
      space: 1,
    ),
    bottomSheetTheme: const BottomSheetThemeData(
      backgroundColor: AppColors.surface,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.sheet)),
      ),
    ),
    snackBarTheme: SnackBarThemeData(
      backgroundColor: AppColors.textPrimary,
      contentTextStyle: const TextStyle(color: Colors.white, fontSize: 14),
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.medium),
      ),
    ),
    progressIndicatorTheme: const ProgressIndicatorThemeData(
      color: AppColors.primary,
    ),
  );
}

/// design.md 9.5 Icon Button — 지도 위 44px 흰색 원형/사각 플로팅 버튼.
class MapIconButton extends StatelessWidget {
  const MapIconButton({
    super.key,
    required this.icon,
    required this.onPressed,
    this.selected = false,
    this.tooltip,
  });

  final IconData icon;
  final VoidCallback onPressed;
  final bool selected;
  final String? tooltip;

  @override
  Widget build(BuildContext context) {
    final button = Material(
      color: AppColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.medium),
        side: const BorderSide(color: AppColors.border),
      ),
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(AppRadius.medium),
        child: SizedBox(
          width: 44,
          height: 44,
          child: Icon(
            icon,
            size: 22,
            color: selected ? AppColors.primary : AppColors.iconDefault,
          ),
        ),
      ),
    );
    final decorated = DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(AppRadius.medium),
        boxShadow: appShadow,
      ),
      child: button,
    );
    if (tooltip == null) return decorated;
    return Tooltip(message: tooltip!, child: decorated);
  }
}
