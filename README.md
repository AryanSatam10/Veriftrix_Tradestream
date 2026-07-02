TradeStream: Enterprise TBML Detection Engine

TradeStream is an institutional-grade document intelligence platform designed to detect Trade-Based Money Laundering (TBML) in real-time. By leveraging multimodal LLMs for document extraction and unsupervised machine learning for anomaly detection, TradeStream automates compliance workflows while providing transparent, explainable risk assessments for financial analysts.

Key Features

* Multimodal OCR Extraction:Utilizes state-of-the-art LLMs to convert unstructured commercial invoices into structured JSON telemetry.
* Isolation Forest Anomaly Detection:Implements unsupervised machine learning to identify financial discrepancies, such as unit-price inflation and commodity-to-price ratio anomalies.
* Explainable AI (XAI):Translates complex model scores into human-readable "Key Risk Drivers," ensuring regulatory transparency and trust for non-technical stakeholders.
* Idempotency & Duplicate Protection:Enterprise-grade safeguards prevent the processing of duplicate documents, eliminating the risk of double-billing and data corruption.
* Persistent Audit Ledger:Built-in local persistence ensures all transaction histories, analyst decisions, and compliance statuses survive server restarts.
* Human-in-the-Loop (HITL) Integration:Provides an intuitive interface for analysts to review, reject, or clear flagged transactions, with decisions written back to the persistent audit log.

Tech Stack

* Backend:FastAPI (Python), Uvicorn, Pydantic
* AI/ML:Google Gemini API (Multimodal Extraction), Scikit-learn (Isolation Forest)
* Frontend:React.js, Tailwind CSS, Vite, Recharts, Lucide-React
* Architecture:Dockerized microservices, Persistent JSON caching, RESTful API

Architectural Highlights

* Idempotent API Design:Safeguards against duplicate document ingestion through transaction ID hashing.
* Financial Data Integrity:Ensures precision by calculating unit-price variance rather than relying on raw total amounts for anomaly detection.
* Professional Reporting:Supports functional CSV exports for downstream auditing and offline regulatory reporting.

Setup & Installation

Prerequisites

Docker & Docker Compose
A valid Google Gemini API Key



Developed for advanced trade finance compliance and automated regulatory reporting.
