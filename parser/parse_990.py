import os
import re
import webbrowser
import pandas as pd
from bs4 import BeautifulSoup

from utilities.helpers import makedirs, write_file


def safe_text(parent, tag, default=""):
    """
    Safely retrieve text from an XML tag.

    Returns the default value if:
    - parent is None
    - tag is not found
    - tag has no text
    """
    if parent is None:
        return default

    el = parent.find(tag)

    if el is None or el.text is None:
        return default

    return el.text.strip()


def safe_int(parent, tag):
    """
    Safely retrieve an integer from an XML tag.

    Returns 0 if the tag is missing or cannot be
    converted to an integer.
    """
    val = safe_text(parent, tag)

    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def find_xml_files(xml_dir):
    """
    Find all XML files in the selected directory.

    Only files in the selected directory itself are included.
    Subdirectories are not searched.

    Returns:
        A sorted list of full XML file paths.
    """

    if not os.path.isdir(xml_dir):
        raise ValueError(
            f"The XML source folder does not exist or is not a folder:\n{xml_dir}"
        )

    xml_files = []

    for filename in os.listdir(xml_dir):
        full_path = os.path.join(xml_dir, filename)

        if (
            os.path.isfile(full_path)
            and filename.lower().endswith(".xml")
        ):
            xml_files.append(full_path)

    # Sort files alphabetically for predictable processing order
    xml_files.sort(key=lambda x: os.path.basename(x).lower())

    return xml_files


def run_990_parser(
    xml_dir,
    results_dir,
    show_board="Yes",
    show_staff="Yes",
    progress_callback=None
):
    """
    Parse Form 990 XML files stored in a local directory.

    Args:
        xml_dir:
            Folder containing downloaded Form 990 XML files.

        results_dir:
            Folder where output files will be written.

        show_board:
            Currently retained for compatibility with the previous
            parser interface.

        show_staff:
            Currently retained for compatibility with the previous
            parser interface.

        progress_callback:
            Optional function used by the GUI to receive status messages.

    Generates:
        - people.csv
        - orgs.csv
        - financial.csv
        - financial_changes.csv
        - summary.html
        - processing_errors.csv (only if errors occur)

    Returns:
        Dictionary containing the paths to generated output files.
    """

    # ---------------------------------------------------------
    # Helper function for sending status messages
    # ---------------------------------------------------------

    def report(message):
        print(message)

        if progress_callback is not None:
            progress_callback(message)

    # ---------------------------------------------------------
    # Create output directory
    # ---------------------------------------------------------

    makedirs(results_dir)

    # ---------------------------------------------------------
    # Output filenames
    # ---------------------------------------------------------

    html_filename = os.path.join(
        results_dir,
        "summary.html"
    )

    people_csv = os.path.join(
        results_dir,
        "people.csv"
    )

    orgs_csv = os.path.join(
        results_dir,
        "orgs.csv"
    )

    financial_csv = os.path.join(
        results_dir,
        "financial.csv"
    )

    financial_changes_csv = os.path.join(
        results_dir,
        "financial_changes.csv"
    )

    errors_csv = os.path.join(
        results_dir,
        "processing_errors.csv"
    )

    # ---------------------------------------------------------
    # Find XML files
    # ---------------------------------------------------------

    xml_files = find_xml_files(xml_dir)

    if not xml_files:
        raise ValueError(
            "No XML files were found in the selected source folder."
        )

    report(
        f"Found {len(xml_files)} XML file(s) in source folder."
    )

    # ---------------------------------------------------------
    # Initialize DataFrames
    # ---------------------------------------------------------

    df_orgs = pd.DataFrame(
        columns=[
            "org_id",
            "ein",
            "org_name",
            "year",
            "voting_members",
            "employees",
            "highest_comp_name",
            "highest_comp_title",
            "highest_comp_amount"
        ]
    )

    df_people = pd.DataFrame(
        columns=[
            "org_id",
            "org_name",
            "year",
            "name",
            "role",
            "job_title",
            "comp",
            "reportable_comp",
            "other_comp",
            "total_comp"
        ]
    )

    df_report = pd.DataFrame(
        columns=[
            "org_id",
            "summary_text"
        ]
    )

    df_financial = pd.DataFrame(
        columns=[
            "org_id",
            "ein",
            "org_name",
            "year",
            "employees",
            "total_revenue",
            "total_expenses",
            "salaries",
            "rev_minus_exp",
            "assets",
            "liabilities",
            "unrestricted_net_assets",
            "program_expenses",
            "current_ratio",
            "debt_ratio",
            "savings_indicator_ratio",
            "operating_margin",
            "program_expense_ratio"
        ]
    )

    # ---------------------------------------------------------
    # Track processing errors
    # ---------------------------------------------------------

    error_rows = []

    processed_count = 0
    skipped_count = 0
    error_count = 0

    # ---------------------------------------------------------
    # Process each local XML file
    # ---------------------------------------------------------

    for index, xml_file in enumerate(xml_files, start=1):

        filename = os.path.basename(xml_file)

        report(
            f"Processing file {index}/{len(xml_files)}: {filename}"
        )

        try:

            # -------------------------------------------------
            # Read local XML file
            # -------------------------------------------------

            with open(
                xml_file,
                "rb"
            ) as f:

                xml_content = f.read()

            soup = BeautifulSoup(
                xml_content,
                "xml"
            )

            # -------------------------------------------------
            # Validate XML
            # -------------------------------------------------

            if not soup.find("Return"):

                message = (
                    f"Skipping invalid XML: {filename} "
                    "(Return element not found)"
                )

                report(message)

                error_rows.append(
                    {
                        "filename": filename,
                        "file_path": xml_file,
                        "error": "Invalid Form 990 XML: Return element not found"
                    }
                )

                skipped_count += 1

                continue

            # -------------------------------------------------
            # Filer information
            # -------------------------------------------------

            filer = soup.find("Filer")

            if filer is None:

                message = (
                    f"Skipping invalid XML: {filename} "
                    "(Filer element not found)"
                )

                report(message)

                error_rows.append(
                    {
                        "filename": filename,
                        "file_path": xml_file,
                        "error": "Filer element not found"
                    }
                )

                skipped_count += 1

                continue

            ein = safe_text(
                filer,
                "EIN"
            )

            org_name = safe_text(
                filer,
                "BusinessName"
            ).title()

            year = int(
                safe_text(
                    soup,
                    "TaxYr",
                    0
                )
            )

            # -------------------------------------------------
            # Create organization ID
            # -------------------------------------------------

            org_id = re.sub(
                "[^a-zA-Z0-9]",
                "",
                f"{org_name}_{year}"
                .replace(" ", "_")
                .lower()
            )

            # -------------------------------------------------
            # Financial / organization information
            # -------------------------------------------------

            voting_members = safe_int(
                soup,
                "VotingMembersGoverningBodyCnt"
            )

            employees = safe_int(
                soup,
                "TotalEmployeeCnt"
            )

            total_revenue = safe_int(
                soup,
                "CYTotalRevenueAmt"
            )

            salaries = safe_int(
                soup,
                "CYSalariesCompEmpBnftPaidAmt"
            )

            total_expenses = safe_int(
                soup,
                "CYTotalExpensesAmt"
            )

            rev_minus_exp = safe_int(
                soup,
                "CYRevenuesLessExpensesAmt"
            )

            assets = safe_int(
                soup,
                "NetAssetsOrFundBalancesEOYAmt"
            )

            liabilities = safe_int(
                soup,
                "TotalLiabilitiesEOYAmt"
            )

            unr_grp = soup.find(
                "NoDonorRestrictionNetAssetsGrp"
            )

            unrestricted_net_assets = (
                safe_int(
                    unr_grp,
                    "EOYAmt"
                )
                if unr_grp
                else 0
            )

            program_expenses = safe_int(
                soup,
                "TotalProgramServiceExpensesAmt"
            )

            report(
                f"  Organization: {org_name}"
            )

            report(
                f"  Tax Year: {year}"
            )

            # -------------------------------------------------
            # Financial ratios
            # -------------------------------------------------

            current_ratio = (
                round(
                    assets / liabilities,
                    3
                )
                if liabilities > 0
                else 0
            )

            debt_ratio = (
                round(
                    liabilities / unrestricted_net_assets,
                    3
                )
                if unrestricted_net_assets > 0
                else 0
            )

            savings_indicator_ratio = (
                round(
                    rev_minus_exp / total_expenses,
                    3
                )
                if total_expenses > 0
                else 0
            )

            operating_margin = (
                round(
                    rev_minus_exp / total_revenue,
                    3
                )
                if total_revenue > 0
                else 0
            )

            program_expense_ratio = (
                round(
                    program_expenses / total_expenses,
                    3
                )
                if total_expenses > 0
                else 0
            )

            # -------------------------------------------------
            # People & compensation
            # -------------------------------------------------

            comp_list = []

            for x in soup.find_all(
                "Form990PartVIISectionAGrp"
            ):

                name = safe_text(
                    x,
                    "PersonNm",
                    "Unknown"
                ).title()

                job_title = safe_text(
                    x,
                    "TitleTxt",
                    "Unknown"
                ).title()

                comp = safe_int(
                    x,
                    "ReportableCompFromOrgAmt"
                )

                reportable_comp = safe_int(
                    x,
                    "ReportableCompFromRltdOrgAmt"
                )

                other_comp = safe_int(
                    x,
                    "OtherCompensationAmt"
                )

                total_comp = (
                    comp
                    + reportable_comp
                    + other_comp
                )

                comp_list.append(
                    total_comp
                )

                tag_names = [
                    t.name
                    for t in x
                    if t.name
                ]

                role = (
                    "Board Member"
                    if (
                        "IndividualTrusteeOrDirectorInd"
                        in tag_names
                        or
                        "InstitutionalTrusteeInd"
                        in tag_names
                    )
                    else "Employee"
                )

                df_people.loc[
                    len(df_people)
                ] = [
                    org_id,
                    org_name,
                    year,
                    name,
                    role,
                    job_title,
                    comp,
                    reportable_comp,
                    other_comp,
                    total_comp
                ]

            # -------------------------------------------------
            # Highest compensation
            # -------------------------------------------------

            comp_list.sort(
                reverse=True
            )

            high = (
                comp_list[0]
                if comp_list
                else 0
            )

            df_highest = df_people[
                (df_people["total_comp"] == high)
                &
                (df_people["year"] == year)
                &
                (df_people["org_name"] == org_name)
            ]

            highest_comp_name = (
                df_highest["name"].iloc[0]
                if not df_highest.empty
                else "NA"
            )

            highest_comp_title = (
                df_highest["job_title"].iloc[0]
                if not df_highest.empty
                else "NA"
            )

            # -------------------------------------------------
            # Append organization data
            # -------------------------------------------------

            df_orgs.loc[
                len(df_orgs)
            ] = [
                org_id,
                ein,
                org_name,
                year,
                voting_members,
                employees,
                highest_comp_name,
                highest_comp_title,
                high
            ]

            # -------------------------------------------------
            # Append financial data
            # -------------------------------------------------

            df_financial.loc[
                len(df_financial)
            ] = [
                org_id,
                ein,
                org_name,
                year,
                employees,
                total_revenue,
                total_expenses,
                salaries,
                rev_minus_exp,
                assets,
                liabilities,
                unrestricted_net_assets,
                program_expenses,
                current_ratio,
                debt_ratio,
                savings_indicator_ratio,
                operating_margin,
                program_expense_ratio
            ]

            # -------------------------------------------------
            # HTML summary per organization
            # -------------------------------------------------

            summary_text = f"""
            <h2 id="{org_id}">{org_name} - {year}</h2>
            <ul>
                <li><b>Employees</b>: {employees}</li>
                <li><b>Total Revenue</b>: ${total_revenue:,}</li>
                <li><b>Total Expenses</b>: ${total_expenses:,}</li>
                <li><b>Assets</b>: ${assets:,}</li>
            </ul>
            """

            df_report.loc[
                len(df_report)
            ] = [
                org_id,
                summary_text
            ]

            processed_count += 1

            report(
                f"  Successfully processed: "
                f"{org_name} - {year}"
            )

        except Exception as e:

            error_count += 1

            error_message = str(e)

            report(
                f"  ERROR processing {filename}: "
                f"{error_message}"
            )

            error_rows.append(
                {
                    "filename": filename,
                    "file_path": xml_file,
                    "error": error_message
                }
            )

    # ---------------------------------------------------------
    # Save processing errors
    # ---------------------------------------------------------

    if error_rows:

        pd.DataFrame(
            error_rows
        ).to_csv(
            errors_csv,
            index=False
        )

        report(
            f"Processing errors saved to: "
            f"{errors_csv}"
        )

    # ---------------------------------------------------------
    # Save main CSV files
    # ---------------------------------------------------------

    df_people.sort_values(
        [
            "org_name",
            "year"
        ],
        ascending=[
            True,
            False
        ]
    ).to_csv(
        people_csv,
        index=False
    )

    df_orgs.sort_values(
        [
            "org_name",
            "year"
        ],
        ascending=[
            True,
            False
        ]
    ).to_csv(
        orgs_csv,
        index=False
    )

    df_financial.sort_values(
        [
            "org_name",
            "year"
        ],
        ascending=[
            True,
            False
        ]
    ).to_csv(
        financial_csv,
        index=False
    )

    report(
        f"Saved people.csv to {people_csv}"
    )

    report(
        f"Saved orgs.csv to {orgs_csv}"
    )

    report(
        f"Saved financial.csv to {financial_csv}"
    )

    # ---------------------------------------------------------
    # Multi-year financial changes
    # ---------------------------------------------------------

    change_rows = []

    df_financial_sorted = (
        df_financial.sort_values(
            [
                "org_name",
                "year"
            ]
        )
    )

    def pct_change(curr, prev):

        if (
            prev in [0, None]
            or curr is None
        ):
            return 0

        return (
            (curr - prev)
            / prev
        ) * 100

    for org, g in df_financial_sorted.groupby(
        "org_name"
    ):

        g = g.sort_values(
            "year"
        )

        first = g.iloc[0]

        last = g.iloc[-1]

        # -----------------------------------------------------
        # Overall change
        # -----------------------------------------------------

        change_rows.append(
            {
                "org_name": org,

                "start_year":
                    first["year"],

                "end_year":
                    last["year"],

                "type":
                    "overall",

                "revenue_change":
                    last["total_revenue"]
                    - first["total_revenue"],

                "revenue_change_pct":
                    pct_change(
                        last["total_revenue"],
                        first["total_revenue"]
                    ),

                "expenses_change":
                    last["total_expenses"]
                    - first["total_expenses"],

                "expenses_change_pct":
                    pct_change(
                        last["total_expenses"],
                        first["total_expenses"]
                    ),

                "assets_change":
                    last["assets"]
                    - first["assets"],

                "operating_margin_change_pct":
                    pct_change(
                        last["operating_margin"],
                        first["operating_margin"]
                    ),

                "program_expense_ratio_change_pct":
                    pct_change(
                        last["program_expense_ratio"],
                        first["program_expense_ratio"]
                    ),

                "debt_ratio_change_pct":
                    pct_change(
                        last["debt_ratio"],
                        first["debt_ratio"]
                    ),

                "current_ratio_change_pct":
                    pct_change(
                        last["current_ratio"],
                        first["current_ratio"]
                    )
            }
        )

        # -----------------------------------------------------
        # Year-to-year changes
        # -----------------------------------------------------

        for i in range(
            1,
            len(g)
        ):

            prev = g.iloc[
                i - 1
            ]

            curr = g.iloc[
                i
            ]

            change_rows.append(
                {
                    "org_name": org,

                    "start_year":
                        prev["year"],

                    "end_year":
                        curr["year"],

                    "type":
                        "year_to_year",

                    "revenue_change":
                        curr["total_revenue"]
                        - prev["total_revenue"],

                    "revenue_change_pct":
                        pct_change(
                            curr["total_revenue"],
                            prev["total_revenue"]
                        ),

                    "expenses_change":
                        curr["total_expenses"]
                        - prev["total_expenses"],

                    "expenses_change_pct":
                        pct_change(
                            curr["total_expenses"],
                            prev["total_expenses"]
                        ),

                    "assets_change":
                        curr["assets"]
                        - prev["assets"],

                    "operating_margin_change_pct":
                        pct_change(
                            curr["operating_margin"],
                            prev["operating_margin"]
                        ),

                    "program_expense_ratio_change_pct":
                        pct_change(
                            curr["program_expense_ratio"],
                            prev["program_expense_ratio"]
                        ),

                    "debt_ratio_change_pct":
                        pct_change(
                            curr["debt_ratio"],
                            prev["debt_ratio"]
                        ),

                    "current_ratio_change_pct":
                        pct_change(
                            curr["current_ratio"],
                            prev["current_ratio"]
                        )
                }
            )

    pd.DataFrame(
        change_rows
    ).to_csv(
        financial_changes_csv,
        index=False
    )

    report(
        f"Saved financial_changes.csv to "
        f"{financial_changes_csv}"
    )

    # ---------------------------------------------------------
    # HTML summary
    # ---------------------------------------------------------

    doc_intro = (
        "<h2>Summary of Form 990s</h2>"
        "<ul>"
    )

    doc_body = ""

    for _, y in df_orgs.iterrows():

        doc_intro += (
            f'<li>'
            f'<a href="#{y["org_id"]}">'
            f'{y["org_name"]} - {y["year"]}'
            f'</a>'
            f'</li>'
        )

        matching_report = df_report[
            df_report["org_id"]
            == y["org_id"]
        ]

        if not matching_report.empty:

            doc_body += (
                matching_report[
                    "summary_text"
                ].iloc[0]
            )

        doc_body += "<hr>"

    doc_intro += "</ul>"

    write_file(
        html_filename,
        doc_intro + doc_body
    )

    report(
        f"Saved HTML summary to "
        f"{html_filename}"
    )

    # ---------------------------------------------------------
    # Processing summary
    # ---------------------------------------------------------

    report("")
    report("===================================")
    report("PARSING COMPLETE")
    report("===================================")

    report(
        f"XML files found: {len(xml_files)}"
    )

    report(
        f"Successfully processed: {processed_count}"
    )

    report(
        f"Skipped invalid files: {skipped_count}"
    )

    report(
        f"Files with errors: {error_count}"
    )

    report(
        f"Results folder: {results_dir}"
    )

    report(
        "==================================="
    )

    # ---------------------------------------------------------
    # Open HTML summary
    # ---------------------------------------------------------

    if os.path.exists(
        html_filename
    ):

        webbrowser.open(
            os.path.abspath(
                html_filename
            )
        )

    # ---------------------------------------------------------
    # Return output paths
    # ---------------------------------------------------------

    outputs = {
        "people_csv":
            people_csv,

        "orgs_csv":
            orgs_csv,

        "financial_csv":
            financial_csv,

        "financial_changes_csv":
            financial_changes_csv,

        "html_summary":
            html_filename
    }

    if error_rows:

        outputs[
            "processing_errors_csv"
        ] = errors_csv

    return outputs


# -------------------------------------------------------------
# Run directly from command line
# -------------------------------------------------------------

if __name__ == "__main__":

    run_990_parser(
        xml_dir="data/xml",
        results_dir="results"
    )
