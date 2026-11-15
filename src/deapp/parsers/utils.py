def normalize_report_table(table) -> list[list]:
    rows = []

    # Keep track of values carried down by rowspan
    rowspan_memory = {}

    # Keep track of the last non-empty value in each column
    previous_values = {}

    # Number of columns (from header)
    header = table.find("tr")
    column_count = len(header.find_all(["td", "th"]))

    for tr in table.find_all("tr"):

        html_cells = tr.find_all(["td", "th"], recursive=False)

        row = []
        html_index = 0

        for col in range(column_count):

            # ----------------------------
            # Is this column occupied by a rowspan?
            # ----------------------------

            if col in rowspan_memory:

                text, remaining = rowspan_memory[col]

                row.append(text)
                previous_values[col] = text

                remaining -= 1

                if remaining == 0:
                    del rowspan_memory[col]
                else:
                    rowspan_memory[col] = (text, remaining)

                continue

            # ----------------------------
            # Read next HTML cell
            # ----------------------------

            if html_index >= len(html_cells):

                text = ""

            else:

                cell = html_cells[html_index]
                html_index += 1

                text = " ".join(cell.stripped_strings)

                rowspan = int(cell.get("rowspan", 1))

                if rowspan > 1:
                    rowspan_memory[col] = (text, rowspan - 1)

            # ----------------------------
            # Business rule:
            # Empty Stage or Item means continue previous value
            # ----------------------------

            if text == "" and col in (0, 1):
                text = previous_values.get(col, "")

            # Remember last non-empty value
            if text != "":
                previous_values[col] = text

            row.append(text)

        rows.append(row)

    return rows
