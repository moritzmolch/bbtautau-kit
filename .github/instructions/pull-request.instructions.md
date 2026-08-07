# Pull Request Instructions

## PR Description Format

When writing PR descriptions, follow these conventions:

### Required Sections
Every PR description must include:
- **Overview**: Brief summary of the change
- **Key Changes**: Bullet points of modifications
- **Testing**: How the changes were tested
- **Checklist**: Link to or include the review checklist

### Optional Sections (include when applicable)
- **Breaking Changes**: Clearly mark with ⚠️ emoji
- **Migration Notes**: Steps for users to adapt
- **Related Issues**: Reference issue numbers
- **Screenshots/Examples**: For UI or behavior changes

## Code Quality Standards

### Before Submitting PR
- [ ] All tests pass (`pytest` or project test command)
- [ ] No new linting errors introduced
- [ ] Type hints added/updated for public APIs
- [ ] Documentation updated if behavior changed
- [ ] Commit messages follow conventional format

### Review Priorities
1. **Correctness**: Does the code work as intended?
2. **Clarity**: Is the code readable and well-documented?
3. **Testing**: Are edge cases covered?
4. **Performance**: Any obvious inefficiencies?
5. **Security**: Any potential vulnerabilities?

## Project-Specific Guidelines

### Python Projects
- Follow PEP 8 style guidelines
- Use type annotations for function signatures
- Include docstrings for public functions and classes
- Prefer explicit imports over wildcard imports

### Testing Requirements
- Unit tests for new functionality
- Integration tests for complex workflows
- Maintain or improve code coverage
- Test edge cases and error conditions

## Branch Naming Convention

Use the following format:
- `feature/description` - New features
- `fix/description` - Bug fixes
- `refactor/description` - Code refactoring
- `docs/description` - Documentation updates
- `test/description` - Test additions/modifications

## Merge Strategy

- **Squash merge** for feature branches with multiple commits
- **Rebase merge** for keeping linear history on small fixes
- **Merge commit** for preserving complete branch history when needed
