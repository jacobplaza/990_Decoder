import os
import re
import webbrowser
import pandas as pd
from bs4 import BeautifulSoup
from utilities.helpers import prep_request, makedirs, write_file


def run_990_parser(source_csv_path, results_dir, show_board="Yes", show_staff="Yes"):
    """
    Parse Form 990 XML files listed in a source CSV and generate:
        - people.csv
        - orgs.csv
        - financial.csv
        - financial_changes.csv
        - HTML summary

    Parameters:
        source_csv_path (str): Path to CSV containing 'source' column with XML URLs
        results_dir (str): Folder to save CSVs and HTML
        show_board (str): "Yes" to include board info in HTML
        show_staff (str): "Yes" to include staff info in HTML

    Returns:
        dict: Paths to generated CSVs and HTML summary
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

    def str_to_int(conv, na):
        try:
            return int(conv)
        except:
            return 0 if na == "number" else "na"

    # --- Read source CSV ---
    df_source = pd.read_csv(source_csv_path)
    source_urls = df_source.source.unique()

    for su in source_urls:
        r = prep_request()
        response = r.get(su, timeout=90)
        soup = BeautifulSoup(response.content, 'xml')

        filer = soup.find('Filer')
        ein = filer.find('EIN').text
        org_name = filer.find('BusinessName').text.strip().title()
        year = int(soup.find('TaxYr').text.strip())
        org_id = re.sub('[^a-zA-Z0-9]', '', f'{org_name}_{year}'.replace(' ', '_').lower())

        # --- Financial / org info ---
        voting_members = str_to_int(soup.find('VotingMembersGoverningBodyCnt').text.strip(), "number")
        employees = str_to_int(soup.find('TotalEmployeeCnt').text.strip(), "number")
        total_revenue = str_to_int(soup.find('CYTotalRevenueAmt').text.strip(), "number")
        salaries = str_to_int(soup.find('CYSalariesCompEmpBnftPaidAmt').text.strip(), "number")
        total_expenses = str_to_int(soup.find('CYTotalExpensesAmt').text.strip(), "number")
        rev_minus_exp = str_to_int(soup.find('CYRevenuesLessExpensesAmt').text.strip(), "number")
        assets = str_to_int(soup.find('NetAssetsOrFundBalancesEOYAmt').text.strip(), "number")

        liab_tag = soup.find('TotalLiabilitiesEOYAmt')
        liabilities = str_to_int(liab_tag.text.strip(), "number") if liab_tag else 0

        unr_tag = soup.find('NoDonorRestrictionNetAssetsGrp')
        unrestricted_net_assets = str_to_int(unr_tag.find('EOYAmt').text.strip(), "number") if unr_tag and unr_tag.find('EOYAmt') else 0

        prog_tag = soup.find('TotalProgramServiceExpensesAmt')
        program_expenses = str_to_int(prog_tag.text.strip(), "number") if prog_tag else 0

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
            name = x.find('PersonNm').text.strip().title()
            job_title = x.find('TitleTxt').text.strip().title()
            comp = str_to_int(x.find('ReportableCompFromOrgAmt').text.strip(), "number")
            reportable_comp = str_to_int(x.find('ReportableCompFromRltdOrgAmt').text.strip(), "number")
            other_comp = str_to_int(x.find('OtherCompensationAmt').text.strip(), "number")
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
    for org, g in df_financial_sorted.groupby('org_name'):
        g = g.sort_values('year')
        first = g.iloc[0]
        last = g.iloc[-1]

        def pct_change(curr, prev):
            if prev in [0, None] or curr is None:
                return 0
            return ((curr - prev) / prev) * 100

        # overall change
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

        # year-to-year changes
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
    print(f"HTML summary opened in browser at {html_filename}")

    return {
        "people_csv": people_csv,
        "orgs_csv": orgs_csv,
        "financial_csv": financial_csv,
        "financial_changes_csv": financial_changes_csv,
        "html_summary": html_filename
    }


if __name__ == "__main__":
    run_990_parser(source_csv_path='data/data_source.csv', results_dir='results')
