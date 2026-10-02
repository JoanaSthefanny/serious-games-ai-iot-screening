from importlib import import_module
from pathlib import Path
import sys

import pandas as pd


PROJECT_NAME = "Serious Games AI-IoT Screening"
PROJECT_VERSION = "1.0.0"

DATABASES = {
    "1": {
        "name": "IEEE Xplore",
        "slug": "ieee",
        "import_module": "importers.ieee",
    },
    "2": {
        "name": "PubMed",
        "slug": "pubmed",
        "import_module": "importers.pubmed",
    },
    "3": {
        "name": "ACM Digital Library",
        "slug": "acm",
        "import_module": "importers.acm",
    },
    "4": {
        "name": "Scopus",
        "slug": "scopus",
        "import_module": "importers.scopus",
    },
    "5": {
        "name": "Engineering Village / Compendex",
        "slug": "compendex",
        "import_module": "importers.compendex",
    },
    "6": {
        "name": "Springer Link",
        "slug": "springer",
        "import_module": "importers.springer",
    },
}

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def print_separator():
    print("=" * 70)


def print_header():
    print()
    print_separator()
    print(PROJECT_NAME.upper())
    print_separator()
    print(f"\nVersion: {PROJECT_VERSION}")


def pause():
    input("\nPress Enter to continue...")


def run_module(module_path, function_name="main", *args, **kwargs):
    """
    Dynamically imports a module and executes one of its functions.

    This allows the public repository to remain modular and prevents
    the entire program from failing when an optional module has not
    yet been installed or created.
    """
    try:
        module = import_module(module_path)

    except ModuleNotFoundError as error:
        print("\nModule not available:")
        print(f"  {module_path}")
        print(
            "\nThis component has not been added "
            "to the repository yet."
        )
        print(f"\nTechnical details: {error}")
        return None

    except Exception as error:
        print("\nAn error occurred while importing the module:")
        print(f"  {module_path}")
        print(f"\nTechnical details: {error}")
        return None

    function = getattr(module, function_name, None)

    if function is None:
        print("\nThe requested function was not found.")
        print(f"Module: {module_path}")
        print(f"Function: {function_name}")
        return None

    try:
        return function(*args, **kwargs)

    except KeyboardInterrupt:
        print("\n\nOperation interrupted by the user.")
        return None

    except Exception as error:
        print("\nAn unexpected error occurred:")
        print(error)
        return None


def show_database_menu(allow_all=False):
    print("\nSelect a database:")
    print()

    for key, database in DATABASES.items():
        print(f"{database['name']:<35} [{key}]")

    if allow_all:
        print(f"{'All databases':<35} [7]")

    print(f"{'Back':<35} [0]")


def select_database(allow_all=False):
    while True:
        show_database_menu(allow_all=allow_all)

        choice = input("\nEnter an option: ").strip()

        if choice == "0":
            return None

        if allow_all and choice == "7":
            return "all"

        if choice in DATABASES:
            return DATABASES[choice]

        print("\nInvalid option.")


def import_records():
    print()
    print_separator()
    print("IMPORT RECORDS")
    print_separator()

    database = select_database()

    if database is None:
        return

    print(f"\nSelected database: {database['name']}")

    run_module(database["import_module"])


def update_master_dataset():
    print()
    print_separator()
    print("UPDATE MASTER DATASET")
    print_separator()

    database = select_database(allow_all=True)

    if database is None:
        return

    if database == "all":
        run_module(
            "data_management.update_master",
            "main",
            database="all",
        )
        return

    print(f"\nSelected database: {database['name']}")

    run_module(
        "data_management.update_master",
        "main",
        database=database["slug"],
    )


def enrich_springer_metadata():
    print()
    print_separator()
    print("SPRINGER METADATA ENRICHMENT")
    print_separator()

    print(
        "\nThis step attempts to retrieve additional metadata "
        "and abstracts using the Springer Nature API."
    )

    run_module("data_management.springer_metadata")


def run_screening():
    print()
    print_separator()
    print("SEMI-AUTOMATED SCREENING")
    print_separator()

    run_module("screening.interactive_screening")


def run_complete_workflow():
    print()
    print_separator()
    print("COMPLETE DATABASE WORKFLOW")
    print_separator()

    database = select_database()

    if database is None:
        return

    print(f"\nSelected database: {database['name']}")
    print("\nThe workflow will perform:")
    print("  1. Record import")

    if database["slug"] == "springer":
        print("  2. Springer metadata enrichment")
        print("  3. Master dataset update")
        print("  4. Screening")
    else:
        print("  2. Master dataset update")
        print("  3. Screening")

    confirmation = input("\nContinue? [y/N]: ").strip().lower()

    if confirmation not in {"y", "yes"}:
        print("\nWorkflow cancelled.")
        return

    print()
    print_separator()
    print("STEP 1 - IMPORT")
    print_separator()

    import_result = run_module(database["import_module"])

    if not isinstance(import_result, pd.DataFrame) or import_result.empty:
        print("\nWorkflow stopped: import did not produce valid records.")
        return

    if database["slug"] == "springer":
        print()
        print_separator()
        print("STEP 2 - SPRINGER METADATA ENRICHMENT")
        print_separator()

        enrichment_result = run_module(
            "data_management.springer_metadata"
        )

        if (
            not isinstance(enrichment_result, pd.DataFrame)
            or enrichment_result.empty
        ):
            print(
                "\nWorkflow stopped: Springer enrichment "
                "did not return saved records."
            )
            print(
                "Check the Springer configuration and "
                "the error shown above before continuing."
            )
            return

    print()
    print_separator()
    print("MASTER DATASET UPDATE")
    print_separator()

    master_result = run_module(
        "data_management.update_master",
        "main",
        database=database["slug"],
    )

    if not isinstance(master_result, pd.DataFrame) or master_result.empty:
        print(
            "\nWorkflow stopped: master dataset update "
            "did not return valid records."
        )
        return

    print()
    print_separator()
    print("SCREENING")
    print_separator()

    print("\nThe interactive screening module will now start.")
    print("Select the same database in the screening menu.")

    run_module("screening.interactive_screening")


def show_about():
    print()
    print_separator()
    print("ABOUT")
    print_separator()

    print(
        "\nSerious Games AI-IoT Screening is a "
        "semi-automated screening pipeline developed "
        "for systematic mapping studies involving:"
    )

    print("\n  - Serious games")
    print("  - Artificial intelligence")
    print("  - Internet of Things")
    print("  - Health applications")

    print("\nThe pipeline combines:")
    print("\n  - Database-specific metadata import")
    print("  - Master dataset management")
    print("  - LLM-assisted evidence classification")
    print("  - Deterministic decision rules")
    print("  - Safety-rescue mechanisms")
    print("  - Manual-review routing")
    print("  - Checkpoint-based execution")


def show_main_menu():
    print_header()

    print("\nWhat would you like to do?")
    print()

    print("Import records                         [1]")
    print("Update master dataset                  [2]")
    print("Enrich Springer metadata               [3]")
    print("Run semi-automated screening           [4]")
    print("Run complete workflow for one database [5]")
    print("About                                  [6]")
    print("Exit                                   [0]")


def main():
    while True:
        show_main_menu()

        choice = input("\nEnter an option: ").strip()

        if choice == "1":
            import_records()
            pause()

        elif choice == "2":
            update_master_dataset()
            pause()

        elif choice == "3":
            enrich_springer_metadata()
            pause()

        elif choice == "4":
            run_screening()
            pause()

        elif choice == "5":
            run_complete_workflow()
            pause()

        elif choice == "6":
            show_about()
            pause()

        elif choice == "0":
            print("\nExiting.")
            print(f"Thank you for using {PROJECT_NAME}.")
            break

        else:
            print("\nInvalid option.")
            pause()


if __name__ == "__main__":
    main()