import csv
import os
import io
import argparse

# --- Part 1: Logic for cleaning from tags ---

# Mappings are now constants at the top level for easy access by all functions.
SECTOR_MAPPING = [
    ('Software, Media & Technology', 'Software & Technology', 1),
    ('Manufacturing & Industrial', 'Manufacturing & Industrial', 2),
    ('construction', 'Manufacturing & Industrial', 2),
    ('Manufacturing & Distribution', 'Manufacturing & Industrial', 2),
    ('Healthcare & Education', 'Healthcare & Education', 3),
    ('Health & Education', 'Healthcare & Education', 3),
    ('Software & Technology', 'Software & Technology', 4),
    ('Business Services', 'Business Services', 7),
    ('Food & Leisure', 'Food & Leisure', 5),
    ('Sustainability', 'Sustainability', 6),
]

CATEGORY_MAPPING = [
    ('Corporate', 'Corporate', 1),
    ('Private Equity', 'Private Equity', 2),
    ('Legal Services', 'Legal Services', 3),
    ('Law Firm', 'Legal Services', 3),
    ('Venture and Capital Growth', 'Venture and Capital Growth', 11),
    ('Financial Services', 'Financial Services', 8),
    ('Wealth Manager', 'Wealth Manager', 9),
    ('Accountants', 'Accountants', 7),
    ('Consultancy', 'Consultancy', 4),
    ('Orion Network', 'Orion Network', 9),
    ('Competitor', 'Competitor', 10),
    ('Debt', 'Debt', 5),
    ('Equity', 'Equity', 6),
    ('Other', 'Other', 99),
]

def _process_field_from_tags(row, field_name, sorted_mapping, valid_values, lower_tags_str):
    """Helper function to update a single field based on tags."""
    current_value = row.get(field_name, '').strip()
    if current_value in valid_values:
        return False

    found_value = None
    for tag, canonical, rank in sorted_mapping:
        if tag.lower() in lower_tags_str:
            found_value = canonical
            break
    
    if found_value and found_value != current_value:
        row[field_name] = found_value
        return True
    
    return False

def clean_from_tags(input_file_object):
    """
    Cleans a CSV file from a file-like object by populating Sector/Category from its Tags column.
    
    Args:
        input_file_object: A file-like object (e.g., from open() or io.StringIO).

    Returns:
        A tuple containing (output_csv_string, updated_rows_count, total_rows_count).
    """
    # Pre-process mappings for efficiency
    sorted_sector_mapping = sorted(SECTOR_MAPPING, key=lambda item: item[2])
    sorted_category_mapping = sorted(CATEGORY_MAPPING, key=lambda item: item[2])
    valid_sectors = {item[1] for item in sorted_sector_mapping}
    valid_categories = {item[1] for item in sorted_category_mapping}

    updated_rows_count = 0
    total_rows_count = 0
    
    # Use io.StringIO to build the output CSV in memory
    output_io = io.StringIO()

    try:
        with input_file_object as infile:
            reader = csv.DictReader(infile)
            if not reader.fieldnames:
                return "", 0, 0

            output_fieldnames = reader.fieldnames[:]
            if 'Sector' not in output_fieldnames:
                output_fieldnames.append('Sector')
            if 'Category' not in output_fieldnames:
                output_fieldnames.append('Category')

            writer = csv.DictWriter(output_io, fieldnames=output_fieldnames)
            writer.writeheader()

            for row in reader:
                total_rows_count += 1
                tags_str = row.get('Tags', '')
                if not tags_str:
                    writer.writerow(row)
                    continue
                
                lower_tags_str = tags_str.lower()
                sector_updated = _process_field_from_tags(row, 'Sector', sorted_sector_mapping, valid_sectors, lower_tags_str)
                category_updated = _process_field_from_tags(row, 'Category', sorted_category_mapping, valid_categories, lower_tags_str)

                if sector_updated or category_updated:
                    updated_rows_count += 1
                
                writer.writerow(row)

        return output_io.getvalue(), updated_rows_count, total_rows_count

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "", 0, 0


# --- Part 2: Logic for enriching from a master file ---

def enrich_from_master(master_file_object, target_file_object):
    """
    Enriches a target CSV using data from a master CSV, using file-like objects.

    Args:
        master_file_object: A file-like object for the master CSV.
        target_file_object: A file-like object for the target CSV.

    Returns:
        A tuple containing (output_csv_string, updated_rows_count, total_rows_count).
    """
    # --- Step 1: Build knowledge base from master file ---
    organisation_data_map = {}
    seen_orgs_lower = set()
    try:
        with master_file_object as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                org_name = row.get('Name', row.get('Organisation', '')).strip()
                if not org_name:
                    continue
                
                if org_name.lower() not in seen_orgs_lower:
                    organisation_data_map[org_name] = {
                        'Sector': row.get('Sector', ''),
                        'Category': row.get('Category', '') 
                    }
                    seen_orgs_lower.add(org_name.lower())
        print(f"Knowledge base built: Found data for {len(organisation_data_map)} unique organisations.")
    except Exception as e:
        print(f"An error occurred while reading the master file: {e}")
        return "", 0, 0

    # --- Step 2: Enrich the target file ---
    updated_rows_count = 0
    total_rows_count = 0
    lower_to_original_key_map = {k.lower(): k for k in organisation_data_map.keys()}
    
    # Use io.StringIO to build the output CSV in memory
    output_io = io.StringIO()

    try:
        with target_file_object as infile:
            reader = csv.DictReader(infile)
            if not reader.fieldnames:
                return "", 0, 0
            
            output_fieldnames = reader.fieldnames[:]
            if 'Sector' not in output_fieldnames:
                output_fieldnames.append('Sector')
            if 'Category' not in output_fieldnames:
                output_fieldnames.append('Category')

            writer = csv.DictWriter(output_io, fieldnames=output_fieldnames)
            writer.writeheader()

            for row in reader:
                total_rows_count += 1
                was_updated = False
                
                org_name = row.get('Organisation', '').strip()
                original_key = lower_to_original_key_map.get(org_name.lower())
                
                if original_key:
                    correct_data = organisation_data_map[original_key]
                    
                    if not row.get('Sector', '').strip() and correct_data.get('Sector'):
                        row['Sector'] = correct_data['Sector']
                        was_updated = True
                    
                    if not row.get('Category', '').strip() and correct_data.get('Category'):
                        row['Category'] = correct_data['Category']
                        was_updated = True
                
                if was_updated:
                    updated_rows_count += 1
                
                writer.writerow(row)

        return output_io.getvalue(), updated_rows_count, total_rows_count

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "", 0, 0

# --- Part 3: Main execution block with command-line parsing ---

def main():
    parser = argparse.ArgumentParser(
        description="A tool for cleaning and enriching CSV data for Capsule.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', required=True, help='Available commands')

    # --- 'clean' command ---
    parser_clean = subparsers.add_parser(
        'clean', 
        help='Cleans a single CSV file by populating Sector/Category from its Tags column.',
        description='Reads a single CSV file, and for each row, it inspects the "Tags" column. \nIf the "Sector" or "Category" fields are empty, it tries to populate them based on predefined mappings.'
    )
    parser_clean.add_argument('--file', required=True, help='The path to the CSV file to clean.')

    # --- 'enrich' command ---
    parser_enrich = subparsers.add_parser(
        'enrich', 
        help='Enriches a target CSV using data from a master CSV.',
        description='Reads a master CSV to build a database of Organisations and their correct Sector/Category. \nIt then processes a target CSV, and for each row, looks up the organisation and fills in \nmissing Sector/Category information.'
    )
    parser_enrich.add_argument('--master', required=True, help='The path to the master organisation CSV file.')
    parser_enrich.add_argument('--target', required=True, help='The path to the target (e.g., people) CSV file to enrich.')

    args = parser.parse_args()

    if args.command == 'clean':
        print(f"--- Running: Clean From Tags on file: {args.file} ---")
        try:
            with open(args.file, mode='r', newline='', encoding='utf-8-sig') as infile:
                output_csv, updated, total = clean_from_tags(infile)
            
            file_dir, file_name = os.path.split(args.file)
            file_base, file_ext = os.path.splitext(file_name)
            output_file_path = os.path.join(file_dir, f"{file_base}_cleaned{file_ext}")

            with open(output_file_path, 'w', encoding='utf-8') as outfile:
                outfile.write(output_csv)

            print("\nProcessing complete.")
            print(f"Total rows processed: {total}")
            print(f"Rows updated: {updated}")
            print(f"Cleaned data saved to: {output_file_path}")

        except FileNotFoundError:
            print(f"Error: The input file was not found at '{args.file}'")

    elif args.command == 'enrich':
        print(f"--- Running: Enrich From Master ---")
        try:
            with open(args.master, mode='r', newline='', encoding='utf-8-sig') as master_file, \
                 open(args.target, mode='r', newline='', encoding='utf-8-sig') as target_file:
                output_csv, updated, total = enrich_from_master(master_file, target_file)

            file_dir, file_name = os.path.split(args.target)
            file_base, file_ext = os.path.splitext(file_name)
            output_file_path = os.path.join(file_dir, f"{file_base}_enriched{file_ext}")

            with open(output_file_path, 'w', encoding='utf-8') as outfile:
                outfile.write(output_csv)

            print("\nProcessing complete.")
            print(f"Total rows processed: {total}")
            print(f"Rows updated: {updated}")
            print(f"Enriched data saved to: {output_file_path}")
        except FileNotFoundError:
            print(f"Error: One of the files was not found. Check paths for --master and --target.")

if __name__ == '__main__':
    main()