# Publishing to PyPI (Trusted Publishing)

1. Create a GitHub repository for this project.
2. In PyPI, create the project `biox` (or your chosen name) and under "Publishing" add a new trusted publisher referencing your GitHub org/repo and the `release.yml` workflow.
3. Push a tag `vX.Y.Z` to GitHub. The `release.yml` workflow will build and publish.

If you prefer API tokens instead of OIDC, set `pypi-token` input on the action and add a repository secret `PYPI_API_TOKEN`.
