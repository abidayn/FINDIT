/// The 9 fixed folders, mirroring `Folder` in backend/models/schemas.py.
///
/// The backend already rejects anything outside this set (its `Folder` is a
/// Pydantic `Literal`), so an unknown value here would mean the two have
/// drifted apart. [Folder.fromLabel] falls back to [Folder.other] rather than
/// throwing — an unrecognised folder is a reason to show the item in the wrong
/// place, not a reason to crash the whole list.
enum Folder {
  selfGrowth('Self Growth'),
  productivity('Productivity'),
  techAndCoding('Tech & Coding'),
  finance('Finance'),
  cookingAndFood('Cooking & Food'),
  fitnessAndHealth('Fitness & Health'),
  entertainment('Entertainment'),
  learning('Learning'),
  other('Other');

  /// The exact string the backend stores and returns.
  final String label;

  const Folder(this.label);

  static Folder fromLabel(String label) {
    return Folder.values.firstWhere(
      (folder) => folder.label == label,
      orElse: () => Folder.other,
    );
  }
}
