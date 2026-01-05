import os
import re
import webbrowser
import pandas as pd
from bs4 import BeautifulSoup
from utilities.helpers import prep_request, makedirs, write_file


def safe_text(parent, tag, default=""):
    el = parent.find(tag)
    if el is None or el.text is None:
        return default
    return el.text.strip()


def safe_int(parent, tag):
    val = safe_text(parent, tag)
    try:
        return int(val)
    except:
        return 0


def run_990_parser(source_csv_path, results_dir, show_board="Yes", show_staff="Yes"):
    """
    Parse Form 990 XML files listed in a source CSV and generate:
        - people.csv
        - orgs.csv
        - financial.csv
        - financial_changes.csv
        - HTML summary
    """

    makedirs(results_dir)

    html_filename = os.path.join(results_dir, 'summary.html')
    people_csv = os.path.join(results_dir, 'people.csv')
    orgs_csv = os.path.join(results_dir, 'orgs.csv')
    financial_csv = os.path.join(results_dir, 'financial.csv')
    financial_changes_csv = os.path.join(results_dir, 'financial_changes.csv')

    # --- Initialize DataFrames ---
    df_orgs = pd.DataFrame(columns=[
        'org_id', 'ein', 'org_name', 'year',
        'voting_members', 'employees',
        'highest_comp_name', 'highest_comp_title', 'highest_comp_amount'
    ])
    df_people = pd.DataFrame(columns=[
        'org_id', 'org_name', 'year',
        'name', 'role', 'job_title',
        'comp', 'reportable_comp', 'other_comp', 'total_comp'
    ])
    df_report = pd.DataFrame(columns=['org_id', 'summary_text'])
    df_financial = pd.DataFrame(columns=[
        'org_id', 'ein', 'org_name', 'year',
        'employees',
        'total_revenue', 'total_expenses', 'salaries',
        'rev_minus_exp', 'assets',
        'liabilities', 'unrestricted_net_assets', 'program_expenses',
        'current_ratio', 'debt_ratio',
        'savings_indicator_ratio', 'operating_margin',
        'program_expense_ratio'
    ])

    # --- Read source CSV ---
    df_source = pd.read_csv(source_csv_path)
    source_urls = df_source.source.unique()

    for su in source_urls:
        r = prep_request()
        response = r.get(su, timeout=90)
        soup = BeautifulSoup(response.content, 'xml')

        # Guard against bad downloads
        if not soup.find('Return'):
            print(f"Skipping invalid XML: {su}")
            continue

        filer = soup.find('Filer')
        ein = safe_text(filer, 'EIN')
        org_name = safe_text(filer, 'BusinessName').title()
        year = int(safe_text(soup, 'TaxYr', 0))

        org_id = re.sub(
            '[^a-zA-Z0-9]',
            '',
            f'{org_name}_{year}'.replace(' ', '_').lower()
        )

        # --- Financial / org info ---
        voting_members = safe_int(soup, 'VotingMembersGoverningBodyCnt')
        employees = safe_int(soup, 'TotalEmployeeCnt')
        total_revenue = safe_int(soup, 'CYTotalRevenueAmt')
        salaries = safe_int(soup, 'CYSalariesCompEmpBnftPaidAmt')
        total_expenses = safe_int(soup, 'CYTotalExpensesAmt')
        rev_minus_exp = safe_int(soup, 'CYRevenuesLessExpensesAmt')
        assets = safe_int(soup, 'NetAssetsOrFundBalancesEOYAmt')

        liabilities = safe_int(soup, 'TotalLiabilitiesEOYAmt')

        unr_grp = soup.find('NoDonorRestrictionNetAssetsGrp')
        unrestricted_net_assets = (
            safe_int(unr_grp, 'EOYAmt') if unr_grp else 0
        )

        program_expenses = safe_int(soup, 'TotalProgramServiceExpensesAmt')

        print(f'Processing data from {org_name} for {year}')

        # ---- Financial ratios ----
        current_ratio = round(assets / liabilities, 3) if liabilities > 0 else 0
        debt_ratio = round(liabilities / unrestricted_net_assets, 3) if unrestricted_net_assets > 0 else 0
        savings_indicator_ratio = round(rev_minus_exp / total_expenses, 3) if total_expenses > 0 else 0
        operating_margin = round(rev_minus_exp / total_revenue, 3) if total_revenue > 0 else 0
        program_expense_ratio = round(program_expenses / total_expenses, 3) if total_expenses > 0 else 0

        # ---- People & compensation ----
        comp_list = []

        for x in soup.find_all('Form990PartVIISectionAGrp'):
            name = safe_text(x, 'PersonNm', 'Unknown').title()
            job_title = safe_text(x, 'TitleTxt', 'Unknown').title()

            comp = safe_int(x, 'ReportableCompFromOrgAmt')
            reportable_comp = safe_int(x, 'ReportableCompFromRltdOrgAmt')
            other_comp = safe_int(x, 'OtherCompensationAmt')
            total_comp = comp + reportable_comp + other_comp
            comp_list.append(total_comp)

            tag_names = [t.name for t in x if t.name]
            role = "Board Member" if (
                "IndividualTrusteeOrDirectorInd" in tag_names or
                "InstitutionalTrusteeInd" in tag_names
            ) else "Employee"

            df_people.loc[len(df_people)] = [
                org_id, org_name, year,
                name, role, job_title,
                comp, reportable_comp, other_comp, total_comp
            ]

        # ---- Highest compensation ----
        comp_list.sort(reverse=True)
        high = comp_list[0] if comp_list else 0

        df_highest = df_people[
            (df_people['total_comp'] == high) &
            (df_people['year'] == year) &
            (df_people['org_name'] == org_name)
        ]

        highest_comp_name = df_highest['name'].iloc[0] if not df_highest.empty else "NA"
        highest_comp_title = df_highest['job_title'].iloc[0] if not df_highest.empty else "NA"

        # ---- Append to orgs / financial DataFrames ----
        df_orgs.loc[len(df_orgs)] = [
            org_id, ein, org_name, year,
            voting_members, employees,
            highest_comp_name, highest_comp_title, high
        ]

        df_financial.loc[len(df_financial)] = [
            org_id, ein, org_name, year,
            employees,
            total_revenue, total_expenses, salaries,
            rev_minus_exp, assets,
            liabilities, unrestricted_net_assets, program_expenses,
            current_ratio, debt_ratio,
            savings_indicator_ratio, operating_margin,
            program_expense_ratio
        ]

        # ---- HTML summary per org ----
        summary_text = f"""
        <h2 id="{org_id}">{org_name} - {year}</h2>
        <ul>
            <li><b>Employees</b>: {employees}</li>
            <li><b>Total Revenue</b>: ${total_revenue:,}</li>
            <li><b>Total Expenses</b>: ${total_expenses:,}</li>
            <li><b>Assets</b>: ${assets:,}</li>
        </ul>
        """
        df_report.loc[len(df_report)] = [org_id, summary_text]

    # ---- Save CSVs ----
    df_people.sort_values(['org_name', 'year'], ascending=[True, False]).to_csv(people_csv, index=False)
    df_orgs.sort_values(['org_name', 'year'], ascending=[True, False]).to_csv(orgs_csv, index=False)
    df_financial.sort_values(['org_name', 'year'], ascending=[True, False]).to_csv(financial_csv, index=False)

    # ---- Multi-year financial changes ----
    change_rows = []
    df_financial_sorted = df_financial.sort_values(['org_name', 'year'])

    def pct_change(curr, prev):
        if prev in [0, None] or curr is None:
            return 0
        return ((curr - prev) / prev) * 100

    for org, g in df_financial_sorted.groupby('org_name'):
        g = g.sort_values('year')
        first = g.iloc[0]
        last = g.iloc[-1]

        change_rows.append({
            'org_name': org,
            'start_year': first['year'],
            'end_year': last['year'],
            'type': 'overall',
            'revenue_change': last['total_revenue'] - first['total_revenue'],
            'revenue_change_pct': pct_change(last['total_revenue'], first['total_revenue']),
            'expenses_change': last['total_expenses'] - first['total_expenses'],
            'expenses_change_pct': pct_change(last['total_expenses'], first['total_expenses']),
            'assets_change': last['assets'] - first['assets'],
            'operating_margin_change_pct': pct_change(last['operating_margin'], first['operating_margin']),
            'program_expense_ratio_change_pct': pct_change(last['program_expense_ratio'], first['program_expense_ratio']),
            'debt_ratio_change_pct': pct_change(last['debt_ratio'], first['debt_ratio']),
            'current_ratio_change_pct': pct_change(last['current_ratio'], first['current_ratio'])
        })

        for i in range(1, len(g)):
            prev = g.iloc[i - 1]
            curr = g.iloc[i]
            change_rows.append({
                'org_name': org,
                'start_year': prev['year'],
                'end_year': curr['year'],
                'type': 'year_to_year',
                'revenue_change': curr['total_revenue'] - prev['total_revenue'],
                'revenue_change_pct': pct_change(curr['total_revenue'], prev['total_revenue']),
                'expenses_change': curr['total_expenses'] - prev['total_expenses'],
                'expenses_change_pct': pct_change(curr['total_expenses'], prev['total_expenses']),
                'assets_change': curr['assets'] - prev['assets'],
                'operating_margin_change_pct': pct_change(curr['operating_margin'], prev['operating_margin']),
                'program_expense_ratio_change_pct': pct_change(curr['program_expense_ratio'], prev['program_expense_ratio']),
                'debt_ratio_change_pct': pct_change(curr['debt_ratio'], prev['debt_ratio']),
                'current_ratio_change_pct': pct_change(curr['current_ratio'], prev['current_ratio'])
            })

    pd.DataFrame(change_rows).to_csv(financial_changes_csv, index=False)
    print(f"Saved financial_changes.csv to {results_dir}")

    # ---- HTML summary ----
    doc_intro = '<h2>Summary of Form 990s</h2><ul>'
    doc_body = ""
    for _, y in df_orgs.iterrows():
        doc_intro += f'<li><a href="#{y["org_id"]}">{y["org_name"]} - {y["year"]}</a></li>'
        doc_body += df_report[df_report['org_id'] == y['org_id']]['summary_text'].iloc[0]
        doc_body += "<hr>"
    doc_intro += "</ul>"

    write_file(html_filename, doc_intro + doc_body)
    webbrowser.open(html_filename)

    return {
        "people_csv": people_csv,
        "orgs_csv": orgs_csv,
        "financial_csv": financial_csv,
        "financial_changes_csv": financial_changes_csv,
        "html_summary": html_filename
    }


if __name__ == "__main__":
    run_990_parser(
        source_csv_path='data/data_source.csv',
        results_dir='results'
    )
