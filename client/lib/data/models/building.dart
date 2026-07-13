class Building {
  const Building({required this.id, required this.name, required this.floors});

  factory Building.fromJson(Map<String, dynamic> json) {
    final floorsJson = json['floors'];
    if (floorsJson is! List) {
      throw const FormatException('Building floors must be a list.');
    }

    return Building(
      id: json['id'] as String,
      name: json['name'] as String,
      floors: floorsJson.map((floor) => floor as int).toList(),
    );
  }

  final String id;
  final String name;
  final List<int> floors;
}
