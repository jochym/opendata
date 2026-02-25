# OpenData Tool - Documentation Index

**Last Updated:** February 25, 2026
**Current Version:** v0.22.31

---

## 📖 User Documentation

### [Testing Guide](TESTING.md)
Everything you need to run tests and verify the installation.

### [AI Setup Guide](AI_SETUP.md)
How to configure AI providers (Google GenAI, OpenAI, etc.).

### [Tester Manual](TESTER_MANUAL.md)
Complete guide for quality assurance and manual testing workflows.

### [Binary System](BINARY_SYSTEM.md)
Detailed description of the CI/CD build and verification system for binaries.

---

## 🛠️ Developer Documentation (`docs/dev/`)

### [Developer Manual](DEVELOPER_MANUAL.md)
Core guide for developers working on the OpenData Tool codebase.

### [API Reference](dev/API.md)
Documentation for the internal REST API used for test automation.

### [Test Infrastructure](dev/TEST_INFRASTRUCTURE.md)
Deep dive into the testing architecture, fixtures, and automated runners.

### [Test Results](dev/TEST_RESULTS.md)
Latest coverage analysis, performance metrics, and historical trends.

### [Field Protocol Design](dev/FIELD_PROTOCOL_DECOUPLING.md)
Architectural details of the 4-layer hierarchical protocol system.

### [Architecture Deep Dives](dev/)
- [Multiprocessing Architecture](dev/MULTIPROCESSING_ARCHITECTURE.md)
- [Prompt System Design](dev/PROMPT_ARCHITECTURE.md)
- [AI Refactoring Notes](dev/AI_REFACTORING.md)

---

## 📈 Project Status

### [Accomplishments](dev/ACCOMPLISHMENTS.md)
Historical development log and major stage achievements.

### [Roadmap](dev/ROADMAP.md)
Future plans and upcoming features.

---

## 🚀 Quick Reference

| Task | Command |
|------|---------|
| **Run All Tests** | `./tests/run_all_tests.sh` |
| **Start App (Dev)** | `python src/opendata/main.py` |
| **Enable API** | `python src/opendata/main.py --api` |
| **Check Version** | `cat src/opendata/VERSION` |

---

**Need Help?** Start with [TESTING.md](TESTING.md) or the [Developer Manual](DEVELOPER_MANUAL.md).
