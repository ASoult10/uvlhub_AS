import os
import zipfile
from pathlib import Path

import click


@click.command("zip", help="Generates a zip file named egc_<uvus>_entrega.zip excluding unnecessary files.")
@click.argument("uvus", required=True)
def create_zip(uvus):
    project_root = Path(os.getenv("WORKING_DIR", ""))
    zip_name = f"egc_{uvus}_entrega.zip"
    zip_path = project_root / zip_name

    # Check if the zip file already exists
    if zip_path.exists():
        if click.confirm(f"The zip file {zip_name} already exists. Do you want to overwrite it?", default=False):
            try:
                zip_path.unlink()  # Remove the existing zip file
                click.echo(click.style(f"Existing zip file {zip_name} removed.", fg="yellow"))
            except Exception as e:
                click.echo(click.style(f"Failed to remove existing zip file: {e}", fg="red"))
                return
        else:
            click.echo(click.style("Operation cancelled. No zip file was created.", fg="yellow"))
            return

    # Check for exactly one .pdf file
    pdf_files = list(project_root.glob("*.pdf"))
    if len(pdf_files) != 1:
        click.echo(
            click.style(f"Error: Expected exactly one .pdf file in the project root. Found {len(pdf_files)}.", fg="red")
        )
        return

    pdf_file = pdf_files[0]

    # Start creating the zip file
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in project_root.iterdir():
            if item.is_dir():
                # Exclude virtual environments
                if (item / "pyvenv.cfg").exists():
                    continue
                # Exclude unwanted directories
                elif item.name in {"rosemary.egg-info", "__pycache__"}:
                    continue
                # Add allowed directories recursively
                for root, dirs, files in os.walk(item):
                    for file in files:
                        file_path = Path(root) / file
                        try:
                            zf.write(file_path, file_path.relative_to(project_root))
                        except Exception as e:
                            click.echo(click.style(f"Failed to add {file_path} to zip: {e}", fg="red"))
            # Exclude specific files
            elif item.name == ".env":  # Exclude only the .env file
                continue
            elif item.suffix == ".zip":  # Exclude any existing .zip files
                continue
            elif item.name in {"app.log"}:  # Exclude logs
                continue
            else:
                # Add allowed files
                try:
                    zf.write(item, item.relative_to(project_root))
                except Exception as e:
                    click.echo(click.style(f"Failed to add {item.name} to zip: {e}", fg="red"))

        # Ensure the .pdf is included only once
        if pdf_file.name not in zf.namelist():
            zf.write(pdf_file, pdf_file.relative_to(project_root))

    click.echo(click.style(f"Zip file created: {zip_path}", fg="green"))
