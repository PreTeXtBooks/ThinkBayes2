# GitHub Pages Setup Guide

This document explains how to complete the GitHub Pages setup for automatically deploying the PreTeXt book.

## Overview

The repository includes a GitHub Actions workflow (`.github/workflows/deploy-pretext.yml`) that automatically builds and deploys the PreTeXt book to GitHub Pages whenever changes are pushed to the `master` branch.

## Required Repository Settings

To enable automatic deployment, you need to configure the following settings in your GitHub repository:

### 1. Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** (top menu)
3. Click **Pages** (left sidebar)
4. Under "Source", select:
   - **GitHub Actions**
5. Click **Save**

**Note**: The workflow uses the official GitHub Actions deployment method, which deploys directly from the workflow without requiring a separate branch.

### 2. Configure Actions Permissions

The workflow already includes the necessary permissions:
- `pages: write` - to deploy to GitHub Pages
- `id-token: write` - for authentication
- `contents: read` - to read repository content

No additional configuration is required in repository settings for permissions.

## How It Works

### Workflow Triggers

The deployment workflow runs automatically when:
- **Push to master**: Builds the book and deploys to GitHub Pages
- **Pull Request**: Builds the book for verification (does not deploy)
- **Manual trigger**: Can be run manually from the Actions tab

### Build Process

1. **Build job**:
   - Checks out the repository code
   - Sets up Python 3.11
   - Installs the PreTeXt CLI (`pretextbook`)
   - Builds the HTML version of the book
   - Uploads the build as a Pages artifact

2. **Deploy job** (only on push to master):
   - Deploys the artifact to GitHub Pages
   - Uses the `github-pages` environment

### Output

After successful deployment, the book will be available at:
- **https://pretextbooks.github.io/ThinkBayes2/**

## Verifying the Setup

After merging this PR to the master branch:

1. Go to the **Actions** tab in your repository
2. You should see the workflow running
3. Once complete, the deploy job will show the deployment URL
4. Visit the GitHub Pages URL to view your book

## Troubleshooting

### Workflow fails with "Permission denied" or "pages: write permission required"
- Ensure GitHub Pages is enabled in Settings > Pages
- Verify the source is set to "GitHub Actions" (not "Deploy from a branch")
- The workflow already has the required permissions configured

### Page not loading after deployment
- Check the Actions tab for any error messages
- Verify the deployment job completed successfully
- It may take a few minutes for GitHub Pages to update
- Check the environment URL in the deployment job output

### Build fails
- Check the Actions logs for specific error messages
- Verify all PreTeXt source files are valid
- Test the build locally: `cd pretext && pretext build web`

## Manual Deployment

To trigger a manual deployment:

1. Go to the **Actions** tab
2. Click on **Build and Deploy PreTeXt Book**
3. Click **Run workflow**
4. Select the branch (master) and click **Run workflow**

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
- [Deploying with GitHub Actions](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site#publishing-with-a-custom-github-actions-workflow)
