# GitHub Pages Setup Guide

This document explains how to complete the GitHub Pages setup for automatically deploying the PreTeXt book.

## Overview

The repository includes a GitHub Actions workflow (`.github/workflows/deploy-pretext.yml`) that automatically builds and deploys the PreTeXt book to GitHub Pages whenever changes are pushed to the `master` or `main` branch.

## Required Repository Settings

To enable automatic deployment, you need to configure the following settings in your GitHub repository:

### 1. Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** (top menu)
3. Click **Pages** (left sidebar)
4. Under "Source", select:
   - **Deploy from a branch**
   - Branch: **gh-pages**
   - Folder: **/ (root)**
5. Click **Save**

**Note**: The `gh-pages` branch will be created automatically by the workflow on its first successful run.

### 2. Configure Actions Permissions

1. In repository **Settings**
2. Click **Actions** > **General** (left sidebar)
3. Scroll to "Workflow permissions"
4. Select **Read and write permissions**
5. (Optional) Check "Allow GitHub Actions to create and approve pull requests"
6. Click **Save**

## How It Works

### Workflow Triggers

The deployment workflow runs automatically when:
- **Push to master/main**: Builds the book and deploys to GitHub Pages
- **Pull Request**: Builds the book for verification (does not deploy)
- **Manual trigger**: Can be run manually from the Actions tab

### Build Process

1. Checks out the repository code
2. Sets up Python 3.11
3. Installs the PreTeXt CLI (`pretextbook`)
4. Builds the HTML version of the book
5. Deploys the generated HTML to the `gh-pages` branch

### Output

After successful deployment, the book will be available at:
- **https://pretextbooks.github.io/ThinkBayes2/**

## Verifying the Setup

After merging this PR to the main/master branch:

1. Go to the **Actions** tab in your repository
2. You should see the workflow running
3. Once complete, check the **gh-pages** branch to see the deployed files
4. Visit the GitHub Pages URL to view your book

## Troubleshooting

### Workflow fails with "Permission denied"
- Check that Actions permissions are set to "Read and write permissions"
- Verify the workflow has `permissions: contents: write` (already configured)

### Page not loading after deployment
- Ensure GitHub Pages is enabled and source is set to `gh-pages` branch
- Check the Actions tab for any error messages
- It may take a few minutes for GitHub Pages to update

### Build fails
- Check the Actions logs for specific error messages
- Verify all PreTeXt source files are valid
- Test the build locally: `cd pretext && pretext build web`

## Manual Deployment

To trigger a manual deployment:

1. Go to the **Actions** tab
2. Click on **Build and Deploy PreTeXt Book**
3. Click **Run workflow**
4. Select the branch and click **Run workflow**

## Local Development

To build and view the book locally:

```bash
# Install PreTeXt CLI
pip install pretextbook

# Build the book
cd pretext
pretext build web

# View in browser
pretext view web
```

## Additional Resources

- [PreTeXt Documentation](https://pretextbook.org/documentation.html)
- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
