# Marathi Plagiarism & Grammar Detection System

> A Web-Based NLP System for Marathi Language using Machine Learning, Deep Learning, and Rule-Based Grammar Checking.

## Overview

The **Marathi Plagiarism & Grammar Detection System** is an NLP-powered web application specifically designed for the Marathi language — a low-resource regional language where advanced linguistic tools are limited.

The system combines **semantic plagiarism detection** with **grammar correction capabilities** to help students, researchers, educators, and content writers analyze Marathi text efficiently.

This project addresses the lack of Marathi-focused NLP tools by integrating modern AI techniques such as **TF-IDF**, **Multilingual BERT**, and a **Rule-Based Grammar Engine**.

---

## Features

### Plagiarism Detection

* Detects similarity between Marathi documents
* Semantic similarity analysis using **Multilingual BERT**
* Traditional text similarity using **TF-IDF**
* Percentage-based plagiarism scoring
* Supports Marathi Unicode text

### Grammar Detection

* Rule-based Marathi grammar checking
* Detects:

  * Spelling mistakes
  * Sentence structure issues
  * Common grammatical errors
  * Punctuation inconsistencies

### Web Application

* User-friendly interface
* Real-time text analysis
* FastAPI backend integration
* Interactive frontend

---

## Technologies Used

### Machine Learning & NLP

* TF-IDF Vectorization
* Multilingual BERT (mBERT)
* Cosine Similarity
* Natural Language Processing (NLP)

### Backend

* FastAPI
* Python

### Frontend

* HTML
* CSS
* JavaScript

### Libraries & Tools

* Scikit-learn
* Transformers (Hugging Face)
* NumPy
* Pandas

---

## Project Structure

```bash
Marathi-Plagiarism-Grammar-Detector/
│
├── backend/
│   ├── plagiarism/
│   ├── grammar/
│   ├── models/
│   └── main.py
│
├── frontend/
│   ├── templates/
│   ├── static/
│   └── index.html
│
├── dataset/
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/prajwalchavan284/Marathi-Plagiarism-Grammar-Detector.git
```

### 2. Navigate to Project Directory

```bash
cd Marathi-Plagiarism-Grammar-Detector
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
uvicorn main:app --reload
```

---

## Usage

1. Open the web application in your browser
2. Enter Marathi text or upload documents
3. Choose:

   * Plagiarism Detection
   * Grammar Checking
4. View the analysis results instantly

---

## Methodology

### Plagiarism Detection Pipeline

1. Text Preprocessing
2. Tokenization
3. TF-IDF Vectorization
4. Semantic Embedding using mBERT
5. Cosine Similarity Calculation
6. Similarity Score Generation

### Grammar Checking Pipeline

1. Marathi Text Parsing
2. Rule Matching
3. Error Identification
4. Suggestion Generation

---

## Objectives

* Promote NLP research for regional Indian languages
* Provide an intelligent plagiarism detection solution for Marathi
* Improve Marathi digital writing quality
* Support educational and academic use cases

---

## Future Enhancements

* Deep grammar correction using Transformer models
* Marathi spell suggestion system
* Voice-to-text integration
* PDF/DOCX document support
* AI-powered writing assistance
* Multi-language plagiarism detection

---

## Contributors

* **Prajwal Chavan**
* Team Members & Project Collaborators

---

## Research & Academic Value

This project contributes toward the advancement of:

* Low-resource language NLP
* Regional language AI systems
* Educational technology
* Semantic text similarity analysis

---

## License

This project is developed for academic and research purposes.

---

## Support

If you found this project useful:

* Star the repository
* Fork the project
* Share feedback and suggestions

---

## Contact

For queries or collaboration opportunities:

**Prajwal Chavan**
GitHub: https://github.com/prajwalchavan284

---
