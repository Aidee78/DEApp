from pathlib import Path
import logging
from types import TracebackType

import xlwings as xw
from deapp.application.exceptions import ExcelWriteError
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
from deapp.services.excel_writer.serialization import to_excel_value


logger = logging.getLogger(__name__)


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
        self._owns_excel_app = False
        self._owns_workbook = False
        self._save = True

        # Save and close matching workbooks already open in Excel.
        for app in list(xw.apps):
            for workbook in list(app.books):
                if Path(workbook.fullname).resolve() == self.wb_path:
                    self.excel_app = app

                    workbook.save()
                    workbook.close()

        # Reuse the matching Excel instance or create a hidden instance.
        try:
            if self.excel_app is None:
                self.excel_app = xw.App(visible=False, add_book=False)
                self._owns_excel_app = True
            self.workbook = self.excel_app.books.open(str(self.wb_path))
            self._owns_workbook = True

        except Exception as error:
            if self._owns_excel_app and self.excel_app is not None:
                try:
                    self.excel_app.quit()
                except Exception as cleanup_error:
                    logger.error(
                        "Excel cleanup after an open failure also failed (%s).",
                        type(cleanup_error).__name__,
                    )
            raise ExcelWriteError("Could not open the local workbook.") from error

    def __enter__(self) -> ExcelManager:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        try:
            self.close_workbook(save=self.save_progress and exc_type is None)
        except Exception as cleanup_error:
            if exc is None:
                raise ExcelWriteError(
                    "Could not close the local workbook cleanly."
                ) from cleanup_error

            logger.error(
                "Workbook cleanup failed while handling %s (%s).",
                exc_type.__name__ if exc_type is not None else "an error",
                type(cleanup_error).__name__,
            )
            exc.add_note(
                "Workbook cleanup also failed "
                f"({type(cleanup_error).__name__})."
            )

        return False

    @property
    def save_progress(self) -> bool:
        return self._save

    @save_progress.setter
    def save_progress(self, value: bool) -> None:
        self._save = value

    def close_workbook(self, save: bool = True) -> None:
        if self._closed:
            return

        errors: list[Exception] = []
        try:
            if save:
                self.workbook.save()
        except Exception as error:
            errors.append(error)

        try:
            if self._owns_workbook:
                self.workbook.close()
        except Exception as error:
            errors.append(error)
        finally:
            # Release the Book COM proxy while its Excel app is still available.
            self.workbook = None

        if self._owns_excel_app and self.excel_app is not None:
            try:
                self.excel_app.quit()
            except Exception as error:
                errors.append(error)

        # The app proxy can be released after quit; the workbook proxy has
        # already been released above.
        self.excel_app = None
        self._closed = True

        if errors:
            failure = ExcelWriteError(
                "Could not save or close the local workbook cleanly."
            )
            for additional_error in errors[1:]:
                failure.add_note(
                    "An additional workbook cleanup step failed "
                    f"({type(additional_error).__name__})."
                )
            raise failure from errors[0]

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
        value = to_excel_value(value)
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

    def _get_worksheet(self, worksheet: str) -> xw.Sheet:
        try:
            return self.workbook.sheets[worksheet]
        except Exception as error:
            raise ExcelWriteError(
                f"Could not find worksheet {worksheet!r}."
            ) from error

    def _write_record(self, record, ws_name, table_name, columns) -> None: 
        try:
            ws = self._get_worksheet(ws_name)
            row = self._next_row(
                ws = ws,
                table_name=table_name,
                columns=columns
            )

            for col, attr in columns:
                field = getattr(record, attr)
                self._write_cell(ws, col, row, field)

        except ExcelWriteError:
            raise
        except Exception as error:
            raise ExcelWriteError(
                "Could not write the blending record to the workbook."
            ) from error
        
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

        self._write_record(
            record=blending_record,
            ws_name=WORKSHEET_NAME,
            table_name=TABLE_NAME,
            columns=COLUMNS,
        )
        
    def write_blistering_record(self, blistering_record: blistering.BlisteringRecord) -> None:
        COLUMNS = [
            ("A", "date"),
            ("B", "machine"),
            ("C", "product"),
            ("D", "batch_number"),
            ("E", "start_time"),
            ("F", "stop_time"),
            ("G", "idle_time"),
            ("I", "output"),
            ("J", "officer"),
            ("K", "status"),
            ("L", "remarks"),
        ]
        
        WORKSHEET_NAME = "BLISTERING"
        TABLE_NAME = "Table20"
        
        self._write_record(
            record=blistering_record,
            ws_name=WORKSHEET_NAME,
            table_name=TABLE_NAME,
            columns=COLUMNS,
        )

    def write_coating_record(self, coating_record: coating.CoatingRecord) -> None:
        COLUMNS = [
            ("A", "date"),
            ("B", "product"),
            ("C", "batch_number"),
            ("D", "officer"),
            ("E", "start_time"),
            ("F", "stop_time"),
            ("H", "quantity_kg"),
            ("I", "quantity_tabs"),
            ("J", "status"),
            ("K", "remarks"),
        ]
        
        WORKSHEET_NAME = "COATING"
        TABLE_NAME = "Table715"
        
        self._write_record(
            record=coating_record,
            ws_name=WORKSHEET_NAME,
            table_name=TABLE_NAME,
            columns=COLUMNS,
        )

    def write_compression_record(self, compression_record: compression.CompressionRecord) -> None:
        COLUMNS = [
            ("A", "date"),
            ("B", "product"),
            ("C", "batch_number"),
            ("D", "officer"),
            ("E", "start_time"),
            ("F", "stop_time"),
            ("H", "quantity_kg"),
            ("I", "quantity_tabs"),
            ("J", "status"),
            ("K", "remarks"),
        ]
        
        WORKSHEET_NAME = "COMPRESSION"
        TABLE_NAME = "Table16"
        
        self._write_record(
            record=compression_record,
            ws_name=WORKSHEET_NAME,
            table_name=TABLE_NAME,
            columns=COLUMNS,
        )

    def write_dispensing_record(self, dispensing_record: dispensing.DispensingRecord) -> None:
        COLUMNS = [
            ("A", "date"),
            ("B", "line"),
            ("C", "product"),
            ("D", "batch_number"),
            ("E", "quantity_kg"),
            ("F", "dispensing_room"),
            ("G", "officer"),
            ("H", "start_time"),
            ("I", "stop_time"),
            ("K", "status"),
            ("L", "remarks"),
        ]
        
        WORKSHEET_NAME = "DISPENSING"
        TABLE_NAME = "Table5"
        
        self._write_record(
            record=dispensing_record,
            ws_name=WORKSHEET_NAME,
            table_name=TABLE_NAME,
            columns=COLUMNS,
        )

    def write_filling_record(self, filling_record: filling.FillingRecord) -> None:
        COLUMNS = [
            ("A", "date"),
            ("B", "line"),
            ("C", "product"),
            ("D", "batch_number"),
            ("E", "start_time"),
            ("F", "stop_time"),
            ("G", "idle_time"),
            ("I", "output"),
            ("K", "drums"),
            ("L", "officer"),
            ("M", "status"),
            ("N", "remarks"),
        ]
        
        WORKSHEET_NAME = "FILLING"
        TABLE_NAME = "Table18"
        
        self._write_record(
            record=filling_record,
            ws_name=WORKSHEET_NAME,
            table_name=TABLE_NAME,
            columns=COLUMNS,
        )

    def write_granulation_record(self, granulation_record: granulation.GranulationRecord) -> None:
        COLUMNS = [
            ("A", "date"),
            ("B", "product"),
            ("C", "batch_number"),
            ("D", "officer"),
            ("E", "start_time"),
            ("F", "stop_time"),
            ("H", "coarse_percent"),
            ("I", "powder_percent"),
            ("J", "status"),
            ("K", "remarks"),
        ]
        
        WORKSHEET_NAME = "GRANULATION"
        TABLE_NAME = "Table13"
        
        self._write_record(
            record=granulation_record,
            ws_name=WORKSHEET_NAME,
            table_name=TABLE_NAME,
            columns=COLUMNS,
        )

    def write_overprinting_record(self, overprinting_record: overprinting.OverprintingRecord) -> None:
        COLUMNS = [
            ("A", "date"),
            ("B", "line"),
            ("C", "product"),
            ("D", "batch_number"),
            ("E", "start_time"),
            ("F", "stop_time"),
            ("G", "idle_time"),
            ("I", "number_of_cartons"),
            ("J", "number_of_packs"),
            ("K", "number_of_bundles"),
            ("L", "number_of_pieces"),
            ("M", "officer"),
            ("N", "status"),
            ("O", "remarks"),
        ]
        
        WORKSHEET_NAME = "OVERPRINTING"
        TABLE_NAME = "Table21"
        
        self._write_record(
            record=overprinting_record,
            ws_name=WORKSHEET_NAME,
            table_name=TABLE_NAME,
            columns=COLUMNS,
        )

    def write_packaging_record(self, packaging_record: packaging.PackagingRecord) -> None:
        COLUMNS = [
            ("A", "date"),
            ("B", "line"),
            ("C", "product"),
            ("D", "batch_number"),
            ("E", "start_time"),
            ("F", "stop_time"),
            ("G", "idle_time"),
            ("I", "number_of_cartons"),
            ("J", "officer"),
            ("K", "status"),
            ("L", "remarks"),
        ]
        
        WORKSHEET_NAME = "PACKAGING"
        TABLE_NAME = "Table17"
        
        self._write_record(
            record=packaging_record,
            ws_name=WORKSHEET_NAME,
            table_name=TABLE_NAME,
            columns=COLUMNS,
        )

    def write_sifting_record(self, sifting_record: sifting.SiftingRecord) -> None:
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
            ("K", "status"),
            ("L", "remarks"),
        ]
        
        WORKSHEET_NAME = "SIFTING"
        TABLE_NAME = "Table6"
        
        self._write_record(
            record=sifting_record,
            ws_name=WORKSHEET_NAME,
            table_name=TABLE_NAME,
            columns=COLUMNS,
        )
