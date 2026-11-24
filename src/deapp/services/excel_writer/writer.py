from pathlib import Path

import xlwings as xw
from deapp.models.excel import (
    blending,
    blistering,
    coating,
    compression,
    dispensing,
    filling,
    granulation,
    overprinting,
    packaging,
    sifting,
)
from deapp.models.excel.field import FlaggedValue


class ExcelManager:

    FLAG_STYLES = {
        2: {"fill": (255, 199, 206), "font": (156, 0, 6)},    # parsing error
        3: {"fill": (255, 235, 156), "font": (156, 87, 0)},   # conflict
    }

    XL_COLOR_INDEX_AUTOMATIC = -4105


    def __init__(self, wb_path: Path) -> None:
        self.wb_path = Path(wb_path).resolve()
        self.excel_app = None
        self._closed = False

        # Save and close matching workbooks already open in Excel.
        for app in list(xw.apps):
            for workbook in list(app.books):
                if Path(workbook.fullname).resolve() == self.wb_path:
                    self.excel_app = app

                    workbook.save()
                    workbook.close()

        # Open the workbook in an Excel instance owned by this manager.
        try:
            self.excel_app = self.excel_app or xw.App(visible=False, add_book=False)
            self.workbook = self.excel_app.books.open(str(self.wb_path))
    
        except Exception as exc:
            if self.excel_app is not None:
                try:
                    self.excel_app.quit()
                except Exception:
                    pass
            
    # Context manager
    def __enter__(self) -> ExcelManager:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            self.close_workbook(save=self.save_progress and exc_type is None):
        except Exception as exc:
            pass

        return False # Don't swallow the exception

    @property
    def save_progress(self) -> bool:
        return self._save

    @save_progress.setter
    def save_progress(self, value: bool) -> None:
        self._save = value

    def close_workbook(self, save: bool = True) -> None:
        if self._closed:
            return

        try:
            if save:
                self.workbook.save()
        finally:
            try:
                if self.workbook_is_mine:
                    self.workbook.close()

            finally:
                if self.workbook_is_mine:
                    self.excel_app.quit()
                self._closed = True

    def _add_table_row(self, ws, table_name) -> int:
        """Append a row to the table and return its worksheet row number."""
        table = ws.tables[table_name]
        new_list_row = table.api.ListRows.Add()
        return new_list_row.Range.Row      # read the row from the object Excel just created

    
    def _next_row(self, ws, table_name, columns) -> int:
        """Return the last table row if blank; otherwise, append a row."""
        table = ws.tables[table_name]
        data_range = table.data_body_range

        if data_range is None:
            return self._add_table_row(ws, table_name)

        first_col = columns[0][0]
        last_col = columns[-1][0]
        last_row = data_range.last_cell.row

        values = ws.range(
            f"{first_col}{last_row}:{last_col}{last_row}"
        ).options(ndim=1).value

        if all(value is None for value in values):
            return last_row

        return self._add_table_row(ws, table_name)

    def _write_cell(self, ws, col: str, row: int, field: FlaggedValue) -> None:
        """Write a value and apply formatting based on its flag."""
        value = field.value
        flag = field.flag

        cell = ws.range(f"{col}{row}")
        cell.value = value

        if flag > 1:
            style = self.FLAG_STYLES.get(flag, self.FLAG_STYLES[2])
            cell.color = style["fill"]
            cell.font.color = style["font"]
            cell.font.bold = True
        else:
            cell.color = None                                       # clear fill
            cell.api.Font.ColorIndex = self.XL_COLOR_INDEX_AUTOMATIC     # remove font color override
            cell.font.bold = False

    def _get_worksheet(self, worksheet):
        try:
            return self.workbook.sheets[worksheet]
        except Exception as exc:
            pass
    
    def write_blending_record(self, blending_record: blending.BlendingRecord) -> None:
        COLUMNS = [
            ("A", "date"),
            ("B", "line"),
            ("C", "product"),
            ("D", "batch_number"),
            ("E", "officer"),
            ("F", "start_time"),
            ("G", "stop_time"),
            ("H", "idle_time"),
            ("J", "quantity_kg"),
            ("K", "drums"),
            ("L", "status"),
            ("M", "remarks"),
        ]

        WORKSHEET_NAME = "BLENDING"
        TABLE_NAME = "Table7"

        try:
            row = self._next_row(
                ws = self._get_worksheet(WORKSHEET_NAME),
                table_name=TABLE_NAME,
                columns= COLUMNS
            )

            for col, attr in COLUMNS:
                self._write_cell(ws, col, row, getattr(blending_record, attr))

        except Exception as exc:
            pass

    def write_blistering_record(self, blistering_record: blistering.BlisteringRecord) -> None:
        pass

    def write_coating_record(self, coating_record: coating.CoatingRecord) -> None:
        pass

    def write_compression_record(self, compression_record: compression.CompressionRecord) -> None:
        pass

    def write_dispensing_record(self, dispensing_record: dispensing.DispensingRecord) -> None:
        pass

    def write_filling_record(self, filling_record: filling.FillingRecord) -> None:
        pass

    def write_granulation_record(self, granulation_record: granulation.GranulationRecord) -> None:
        pass

    def write_overprinting_record(self, overprinting_record: overprinting.OverprintingRecord) -> None:
        pass

    def write_packaging_record(self, packaging_record: packaging.PackagingRecord) -> None:
        pass

    def write_sifting_record(self, sifting_record: sifting.SiftingRecord) -> None:
        pass
