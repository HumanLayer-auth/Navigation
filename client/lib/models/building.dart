class Building {
  const Building({required this.id, required this.name, required this.floors});

  final String id;
  final String name;
  final List<int> floors;

  factory Building.fromJson(Map<String, dynamic> json) {
    return Building(
      id: json['id'] as String,
      name: json['name'] as String,
      floors: (json['floors'] as List<dynamic>).cast<int>(),
    );
  }
}
