import csv
import re
from pathlib import Path


# ============================================================
# ENCO SPROCKET CATALOG
#
# Expected file naming:
#
# enco_asa_80_1.csv
#          │  │
#          │  └── strands
#          └──── ASA size
#
# ============================================================


FILE_PATTERN = re.compile(
    r"enco_asa_(\d+)_(\d+)\.csv$",
    re.IGNORECASE
)


# ============================================================
# DECIMAL CONVERSION
#
# ENCO CSV:
#
# 90,16
# 102,00
# etc.
# ============================================================

def to_float(value):

    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    value = (
        value
        .replace(" ", "")
        .replace(".", "")
        .replace(",", ".")
    )

    return float(value)


# ============================================================
# INTEGER CONVERSION
#
# Example:
#
# "11,00" -> 11
# ============================================================

def to_integer(value):

    number = to_float(value)

    if number is None:
        return None

    rounded = round(number)

    if abs(
        number - rounded
    ) > 1e-9:

        raise ValueError(
            f"Expected integer value, got: {value}"
        )

    return int(rounded)


# ============================================================
# PARSE FILE NAME
# ============================================================

def parse_filename(file_path):

    file_path = Path(
        file_path
    )

    match = FILE_PATTERN.match(
        file_path.name
    )

    if match is None:

        raise ValueError(
            f"Invalid ENCO sprocket filename:\n"
            f"{file_path.name}"
        )

    asa = int(
        match.group(1)
    )

    strands = int(
        match.group(2)
    )

    return asa, strands


# ============================================================
# IDENTIFY DATA ROW
#
# Example ENCO reference:
#
# 1.80.11
# 1.100.20
# ============================================================

def is_data_row(row):

    if not row:
        return False

    reference = (
        str(row[0])
        .strip()
    )

    return bool(
        re.fullmatch(
            r"\d+\.\d+\.\d+",
            reference
        )
    )


# ============================================================
# READ ONE ENCO CSV
# ============================================================

def read_enco_sprocket_file(
    file_path
):

    file_path = Path(
        file_path
    )

    asa_from_filename, strands_from_filename = (
        parse_filename(
            file_path
        )
    )


    records = []


    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.reader(
            file,
            delimiter=";"
        )


        for row_number, row in enumerate(
            reader,
            start=1
        ):

            # Ignore the two ENCO header lines
            # and any other non-data row.

            if not is_data_row(row):
                continue


            if len(row) < 8:

                raise ValueError(
                    f"Invalid row in "
                    f"{file_path.name}, "
                    f"line {row_number}:\n"
                    f"{row}"
                )


            reference = (
                row[0]
                .strip()
            )


            teeth_z = (
                to_integer(
                    row[1]
                )
            )


            dp_catalog_mm = (
                to_float(
                    row[2]
                )
            )


            outside_diameter_mm = (
                to_float(
                    row[3]
                )
            )


            hub_diameter_mm = (
                to_float(
                    row[4]
                )
            )


            total_length_mm = (
                to_float(
                    row[5]
                )
            )


            pilot_bore_mm = (
                to_float(
                    row[6]
                )
            )


            maximum_bore_mm = (
                to_float(
                    row[7]
                )
            )


            # =================================================
            # CROSS-CHECK REFERENCE
            #
            # 1.80.11
            #
            # first number  = strands
            # second number = ASA
            # third number  = teeth
            # =================================================

            parts = reference.split(
                "."
            )


            ref_strands = int(
                parts[0]
            )

            ref_asa = int(
                parts[1]
            )

            ref_teeth = int(
                parts[2]
            )


            warnings = []


            if (
                ref_strands
                != strands_from_filename
            ):

                warnings.append(
                    "STRANDS_FILENAME_REFERENCE_MISMATCH"
                )


            if (
                ref_asa
                != asa_from_filename
            ):

                warnings.append(
                    "ASA_FILENAME_REFERENCE_MISMATCH"
                )


            if (
                ref_teeth
                != teeth_z
            ):

                warnings.append(
                    "TEETH_REFERENCE_VALUE_MISMATCH"
                )


            record = {

                "manufacturer":
                    "ENCO",

                "asa":
                    asa_from_filename,

                "strands":
                    strands_from_filename,

                "teeth_z":
                    teeth_z,

                "reference":
                    reference,

                "dp_catalog_mm":
                    dp_catalog_mm,

                "outside_diameter_mm":
                    outside_diameter_mm,

                "hub_diameter_mm":
                    hub_diameter_mm,

                "total_length_mm":
                    total_length_mm,

                "pilot_bore_mm":
                    pilot_bore_mm,

                "maximum_bore_mm":
                    maximum_bore_mm,

                "source_file":
                    file_path.name,

                "source_row":
                    row_number,

                "warnings":
                    warnings,

                "validation_status":
                    (
                        "VALID"
                        if not warnings
                        else "REVIEW"
                    ),
            }


            records.append(
                record
            )


    return records


# ============================================================
# LOAD COMPLETE ENCO DIRECTORY
# ============================================================

def load_enco_sprocket_catalog(
    directory
):

    directory = Path(
        directory
    )


    if not directory.exists():

        raise FileNotFoundError(
            f"ENCO sprocket directory "
            f"not found:\n"
            f"{directory}"
        )


    files = sorted(
        directory.glob(
            "enco_asa_*_*.csv"
        )
    )


    if not files:

        raise FileNotFoundError(
            f"No ENCO sprocket CSV files "
            f"found in:\n"
            f"{directory}"
        )


    records = []


    for file_path in files:

        file_records = (
            read_enco_sprocket_file(
                file_path
            )
        )


        records.extend(
            file_records
        )


    # ========================================================
    # UNIQUE KEY VALIDATION
    #
    # manufacturer + ASA + strands + teeth
    # ========================================================

    seen = {}


    for record in records:

        key = (

            record[
                "manufacturer"
            ],

            record[
                "asa"
            ],

            record[
                "strands"
            ],

            record[
                "teeth_z"
            ],
        )


        if key in seen:

            raise ValueError(

                "Duplicate sprocket catalog entry:\n"
                f"{key}\n\n"

                f"First: "
                f"{seen[key]['source_file']}\n"

                f"Second: "
                f"{record['source_file']}"
            )


        seen[key] = (
            record
        )


    return records


# ============================================================
# AVAILABLE ASA SIZES
# ============================================================

def get_available_asa_sizes(
    catalog,
    strands=1,
    valid_only=True
):

    values = set()


    for record in catalog:

        if (
            record["strands"]
            != strands
        ):
            continue


        if (
            valid_only
            and
            record[
                "validation_status"
            ]
            != "VALID"
        ):
            continue


        values.add(
            record[
                "asa"
            ]
        )


    return sorted(
        values
    )


# ============================================================
# AVAILABLE TEETH
#
# This function is important for the future GUI.
#
# User selects ASA 80:
#
# -> GUI receives only teeth that actually exist
#    in the ENCO catalog.
# ============================================================

def get_available_teeth(
    catalog,
    asa,
    strands=1,
    valid_only=True
):

    values = []


    for record in catalog:

        if (
            record["asa"]
            != int(asa)
        ):
            continue


        if (
            record["strands"]
            != strands
        ):
            continue


        if (
            valid_only
            and
            record[
                "validation_status"
            ]
            != "VALID"
        ):
            continue


        values.append(
            record[
                "teeth_z"
            ]
        )


    return sorted(
        values
    )


# ============================================================
# GET ONE SPROCKET
# ============================================================

def get_sprocket(
    catalog,
    asa,
    teeth_z,
    strands=1,
    manufacturer="ENCO",
    valid_only=True
):

    matches = []


    for record in catalog:

        if (
            record[
                "manufacturer"
            ]
            != manufacturer
        ):
            continue


        if (
            record["asa"]
            != int(asa)
        ):
            continue


        if (
            record["strands"]
            != int(strands)
        ):
            continue


        if (
            record["teeth_z"]
            != int(teeth_z)
        ):
            continue


        if (
            valid_only
            and
            record[
                "validation_status"
            ]
            != "VALID"
        ):
            continue


        matches.append(
            record
        )


    if len(matches) == 0:

        return None


    if len(matches) > 1:

        raise RuntimeError(

            "Multiple catalog records found "
            f"for ASA {asa}, "
            f"{teeth_z} teeth."
        )


    return matches[0]


# ============================================================
# SUMMARY
# ============================================================

def print_catalog_summary(
    catalog
):

    print()
    print("=" * 72)
    print("ENCO SPROCKET CATALOG")
    print("=" * 72)


    asa_sizes = (
        get_available_asa_sizes(
            catalog,
            valid_only=False
        )
    )


    print(
        f"Total records: "
        f"{len(catalog)}"
    )


    print(
        f"ASA sizes: "
        f"{asa_sizes}"
    )


    print()


    for asa in asa_sizes:

        teeth = (
            get_available_teeth(

                catalog,
                asa,

                valid_only=False
            )
        )


        print(

            f"ASA {asa:3d}-1 | "
            f"{len(teeth):3d} sprockets | "

            f"z = "
            f"{teeth}"
        )


    print()


    review_records = [

        record

        for record
        in catalog

        if (
            record[
                "validation_status"
            ]
            != "VALID"
        )
    ]


    print(
        f"Records requiring review: "
        f"{len(review_records)}"
    )


    for record in review_records:

        print(

            f"  "
            f"{record['reference']} "
            f"| "
            f"{record['warnings']}"
        )


    print("=" * 72)


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    PROJECT_ROOT = Path(__file__).resolve().parents[1]


    ENCO_DIRECTORY = (

        PROJECT_ROOT
        / "data"
        / "sprockets"
        / "enco"
    )


    catalog = (
        load_enco_sprocket_catalog(
            ENCO_DIRECTORY
        )
    )


    print_catalog_summary(
        catalog
    )


    print()
    print("TEST: ASA 80 / 11 teeth")
    print("-" * 72)


    test = get_sprocket(
        catalog,
        asa=80,
        teeth_z=11
    )


    if test is None:

        print(
            "ASA 80 / 11T not found."
        )

    else:

        for key, value in (
            test.items()
        ):

            print(
                f"{key}: {value}"
            )
