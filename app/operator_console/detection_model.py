"""Keyed presentation rows keep Qt delegates stable during RX updates."""

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt


class DetectionListModel(QAbstractListModel):
    RowRole = int(Qt.ItemDataRole.UserRole) + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []

    def roleNames(self):
        return {self.RowRole: b"modelData"}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid() and 0 <= index.row() < len(self._rows) and role == self.RowRole:
            return self._rows[index.row()]
        return None

    def set_rows(self, rows):
        def row_key(row):
            return row.get("rowKey", row["eventId"])

        ids = [row_key(row) for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate presentation row key")
        for index in range(len(self._rows) - 1, -1, -1):
            if row_key(self._rows[index]) not in ids:
                self.beginRemoveRows(QModelIndex(), index, index)
                self._rows.pop(index)
                self.endRemoveRows()
        for index, row in enumerate(rows):
            existing = next((i for i in range(index, len(self._rows)) if row_key(self._rows[i]) == row_key(row)), None)
            if existing is None:
                self.beginInsertRows(QModelIndex(), index, index)
                self._rows.insert(index, dict(row))
                self.endInsertRows()
            else:
                if existing != index:
                    destination = index if existing > index else index + 1
                    if not self.beginMoveRows(
                        QModelIndex(), existing, existing, QModelIndex(), destination
                    ):
                        raise RuntimeError("Qt satır taşıma işlemini reddetti")
                    self._rows.insert(index, self._rows.pop(existing))
                    self.endMoveRows()
                if self._rows[index] != row:
                    self._rows[index] = dict(row)
                    self.dataChanged.emit(self.index(index), self.index(index), [self.RowRole])
