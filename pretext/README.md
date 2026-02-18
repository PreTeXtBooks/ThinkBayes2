# Think Bayes 2 - PreTeXt Edition

This directory contains the PreTeXt source for Think Bayes 2 by Allen B. Downey.

## Building the Book

### Prerequisites

Install the PreTeXt CLI:

```bash
pip install pretextbook
```

### Build HTML

To build the HTML version:

```bash
cd pretext
pretext build web
```

The output will be in `output/web/`.

### View Locally

To view the built book in your browser:

```bash
pretext view web
```

### Build PDF

To build a PDF version (requires LaTeX):

```bash
pretext build print
```

## Automated Deployment

The book is automatically built and deployed to GitHub Pages when changes are pushed to the master/main branch. The deployment is handled by the GitHub Actions workflow in `.github/workflows/deploy-pretext.yml`.

## Project Structure

- `source/` - Contains the PreTeXt source files
  - `main.ptx` - Main book file
  - `ch*.ptx` - Chapter files
  - `meta_*.ptx` - Frontmatter and backmatter
- `publication/` - Publication configuration
- `assets/` - Static assets (images, etc.)
- `output/` - Generated output (not committed to git)

## Learn More

Visit <https://pretextbook.org/documentation.html> to learn more about PreTeXt.