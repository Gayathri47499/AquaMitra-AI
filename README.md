# AquaMitra AI 🐟
### AI-Powered Aquaculture Advisory Assistant

**Making aquaculture knowledge more accessible through domain-specific Generative AI.**

AquaMitra AI is an AI-powered aquaculture advisory assistant designed to help fish farmers access understandable information about water quality, feeding practices, fish health, and pond management through a conversational interface.

The project combines a domain-fine-tuned Large Language Model (LLM) with a full-stack web application, authentication, conversation history, and cloud-hosted inference.

🌐 **Live Application:** https://aquamitra-ai.vercel.app/  
💻 **GitHub Repository:** https://github.com/Gayathri47499/AquaMitra-AI

---

## 📌 Table of Contents

- [Problem Statement](#-problem-statement)
- [Project Objectives](#-project-objectives)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Technology Stack](#-technology-stack)
- [Dataset Preparation](#-dataset-preparation)
- [Model Fine-Tuning](#-model-fine-tuning)
- [Application Workflow](#-application-workflow)
- [Deployment](#-deployment)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Current Limitations](#-current-limitations)
- [Future Enhancements](#-future-enhancements)
- [Disclaimer](#-disclaimer)

---

## 🎯 Problem Statement

Aquaculture plays an important role in food production and livelihoods, but accessing understandable and relevant farming guidance can be challenging for small-scale and family-run fish farms.

Farmers may need information about pond water quality, feeding practices, fish health concerns, and routine pond management. Technical information can also be difficult to navigate when it is distributed across lengthy reference documents.

AquaMitra AI addresses this accessibility challenge through a conversational AI assistant that provides domain-focused guidance in simple English.

The goal is to make aquaculture knowledge easier to access and help users make more informed day-to-day farming decisions.

## 🎯 Project Objectives

- Develop an AI assistant focused on aquaculture-related questions.
- Prepare a domain-specific question-answer dataset from aquaculture reference material.
- Fine-tune an existing language model using parameter-efficient techniques.
- Build an interactive web application for asking questions and receiving generated responses.
- Integrate authentication and persistent conversation history.
- Deploy the frontend, backend, and model-serving components.
- Establish groundwork for future retrieval-augmented generation (RAG).

## ✨ Key Features

- **Aquaculture-focused assistance:** Provides general guidance on water quality, feeding, fish health, and pond management.
- **Domain-specific model adaptation:** Uses a fine-tuned Qwen3 language model.
- **Conversational interface:** Allows users to ask questions in natural language.
- **Authentication:** Integrates user authentication through Supabase.
- **Chat history:** Stores conversations in PostgreSQL.
- **Conversation management:** Supports conversation-history retrieval and deletion.
- **Domain screening:** Includes backend checks intended to restrict questions to the application's intended subject area.
- **Cloud deployment:** Separates the frontend, backend API, and model inference service.
- **Parameter-efficient training:** Uses QLoRA to reduce the memory requirements of fine-tuning.

## 🏗️ System Architecture

The application uses a modular architecture with separate frontend, backend, database, and model-serving components.

```text
                 ┌──────────────────────────┐
                 │       User / Browser     │
                 └────────────┬─────────────┘
                              │
                              ▼
                 ┌──────────────────────────┐
                 │      React Frontend      │
                 │  React + Vite + Tailwind │
                 │        Vercel            │
                 └────────────┬─────────────┘
                              │ HTTP API
                              ▼
                 ┌──────────────────────────┐
                 │      FastAPI Backend     │
                 │          Render          │
                 │                          │
                 │ Request handling         │
                 │ Session and scope checks │
                 │ Model-call coordination  │
                 └──────┬───────────┬───────┘
                        │           │
               ┌────────▼───┐  ┌────▼────────────────┐
               │  Supabase  │  │  Hugging Face Space │
               │ Auth +     │  │  Gradio + ZeroGPU   │
               │ PostgreSQL │  │                     │
               │ Chat history│  │  Qwen3-4B + LoRA    │
               └────────────┘  └─────────────────────┘
```

### Architecture Components

| Component | Responsibility |
|---|---|
| React frontend | User interface, question input, response display, and conversation interactions |
| FastAPI backend | API endpoints, request processing, session checks, scope screening, and service coordination |
| Supabase Auth | User authentication |
| PostgreSQL | Persistent application data and chat history |
| Hugging Face Spaces | Hosts the model-serving application |
| Gradio | Exposes the model inference interface |
| Qwen3-4B + LoRA adapter | Generates aquaculture-related responses |
| Vercel | Frontend hosting |
| Render | Backend hosting |

**Note:** PostgreSQL and pgvector knowledge-store groundwork has been prepared for future RAG integration. Retrieval is not currently connected to the live chat workflow.

## 🛠️ Technology Stack

### Programming Languages
- Python
- JavaScript
- HTML and CSS

### Artificial Intelligence and Deep Learning
- Qwen3-4B-Instruct-2507
- PyTorch
- Hugging Face Transformers
- Supervised Fine-Tuning (SFT)
- Quantized Low-Rank Adaptation (QLoRA)
- Low-Rank Adaptation (LoRA)
- Parameter-Efficient Fine-Tuning (PEFT)
- Unsloth
- TRL
- bitsandbytes

### Frontend
- React
- Vite
- Tailwind CSS
- Framer Motion

### Backend
- FastAPI
- Python

### Database and Authentication
- Supabase Auth
- PostgreSQL

### Model Serving and Deployment
- Hugging Face Spaces
- Gradio
- ZeroGPU
- Vercel
- Render

### Retrieval Groundwork
- pgvector
- Text embeddings

## 📚 Dataset Preparation

The training dataset was prepared using aquaculture reference material, with the ICAR Fisheries Handbook serving as the primary reference source.

The data-preparation workflow included:

1. **Text extraction and cleaning:** Extracting relevant information and preparing eligible passages.
2. **Coverage expansion:** Incorporating additional aquaculture text.
3. **Synthetic data generation:** Creating question-answer pairs from prepared passages.
4. **Deduplication:** Removing exact and near-duplicate examples.
5. **Rule-based filtering:** Applying formatting and length checks.
6. **Review workflow:** Recording reviewer decisions in a separate review sheet.

### Dataset Summary

| Property | Details |
|---|---|
| Primary reference | ICAR Fisheries Handbook |
| Additional source material | Aquaculture text |
| Dataset type | Synthetic question-answer pairs |
| Training dataset | 12,000 pairs |
| Processing | Cleaning, deduplication, and rule-based filtering |

The initial prototype contained 115 hand-written pairs and was expanded to 348 through rule-based augmentation. This earlier prototype was superseded by the synthetic training dataset.

The reported 12,000-pair training run should not be interpreted as proof that every pair was individually approved by a domain expert.

## 🧠 Model Fine-Tuning

AquaMitra AI uses **Qwen3-4B-Instruct-2507**, an instruction-tuned language model with approximately four billion parameters.

Rather than training a language model from scratch, the project uses supervised fine-tuning with QLoRA to adapt the existing model to the target domain.

### Training Configuration

| Parameter | Value |
|---|---|
| Base model | Qwen3-4B-Instruct-2507 |
| Training method | Supervised Fine-Tuning (SFT) |
| Parameter-efficient method | QLoRA / LoRA |
| Base-model quantization | 4-bit during training |
| LoRA rank | 16 |
| LoRA alpha | 32 |
| LoRA dropout | 0 |
| Target modules | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj |
| Training examples | 12,000 question-answer pairs |
| Epochs | 1 |
| Optimization steps | 1,500 |
| Effective batch size | 8 |
| Learning rate | 1 × 10⁻⁴ |
| Maximum sequence length | 1,024 tokens |
| Training precision | BF16 |
| Optimizer | AdamW 8-bit |
| Saved adapter artifact | Approximately 126 MB |

### Why QLoRA?

Full fine-tuning updates the parameters of the entire base model and can require substantial GPU memory.

QLoRA reduces memory requirements by using a quantized base model and training small, low-rank adapter parameters instead of updating all base-model weights.

This makes domain-specific experimentation more practical while retaining the capabilities of the pretrained model.

### Training Workflow

```text
Aquaculture Reference Material
              │
              ▼
     Data Preparation
              │
              ▼
  12,000 Synthetic Q&A Pairs
              │
              ▼
      Dataset Processing
              │
              ▼
       Qwen3-4B Base Model
              │
              ▼
       SFT with QLoRA
              │
              ▼
    Saved LoRA Adapter
              │
              ▼
  Base Model + Adapter Loaded
              │
              ▼
       Model Inference
```

The saved adapter is loaded alongside the compatible base model in the model-serving environment.

Training loss and checkpoint information describe the recorded training run; they do not independently establish real-world answer accuracy.

## 🔄 Application Workflow

1. A user opens the AquaMitra AI web application.
2. The user authenticates through the application.
3. The user submits an aquaculture-related question through the React interface.
4. The frontend sends the request to the FastAPI backend.
5. The backend processes the request and performs the configured session and domain checks.
6. The backend communicates with the model-serving service.
7. The fine-tuned model generates a response.
8. The application processes the returned answer and manages conversation storage.
9. The frontend displays the response and makes conversation history available.

The exact handling of an individual request depends on the configured backend logic and the availability of the model service.

## ☁️ Deployment

The project separates the frontend, backend, and model-serving components.

| Service | Platform | Purpose |
|---|---|---|
| Frontend | Vercel | Hosts the React web application |
| Backend API | Render | Runs the FastAPI service |
| Model inference | Hugging Face Spaces | Serves the model through Gradio |
| Authentication and storage | Supabase | Authentication and PostgreSQL persistence |
| Source code | GitHub | Version control and project repository |

### Live Links

- **Application:** https://aquamitra-ai.vercel.app/
- **GitHub:** https://github.com/Gayathri47499/AquaMitra-AI

## 📁 Project Structure

The application is organized into frontend, backend, model-serving, and training/data components.

```text
AquaMitra-AI/
│
├── frontend/
│   ├── public/
│   ├── src/
│   └── package.json
│
├── backend/
│   ├── API application and routes
│   ├── Request processing
│   └── Model-service integration
│
├── training/
│   ├── Data preparation scripts
│   ├── Fine-tuning configuration
│   └── Training utilities
│
├── data/
│   └── Prepared training data
│
├── models/
│   └── Adapter and model configuration artifacts
│
├── README.md
└── .gitignore
```

*This is a conceptual overview. Actual filenames and directories may differ in the repository. Consult the repository for the authoritative project structure.*

## 🚀 Getting Started

The following is a general local-development workflow. Exact commands and environment variables depend on the actual project files.

### Prerequisites

- Python compatible with the backend dependencies
- Node.js and npm
- Git
- Access to the required Supabase project
- Access to the configured model-serving endpoint

### 1. Clone the repository

```bash
git clone https://github.com/Gayathri47499/AquaMitra-AI.git
cd AquaMitra-AI
```

### 2. Set up the frontend

Navigate to the actual frontend directory:

```bash
cd frontend
npm install
npm run dev
```

Use the scripts defined in the frontend's `package.json` if the commands differ.

### 3. Set up the backend

Navigate to the actual backend directory and create a Python virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies using the dependency file provided by the backend:

```bash
pip install -r requirements-api.txt
```

Configure the required environment variables according to the project's configuration. Start the FastAPI service using the actual application module and startup instructions in the repository.

### 4. Configure environment variables

Depending on the implementation, the application may require configuration for:

- Supabase URL and public client key
- Backend API URL
- Model-service endpoint
- Any server-side credentials required by the implementation

Use a local `.env` file only where supported by the project. Never commit private credentials, access tokens, or secret keys to GitHub.

### 5. Model setup

The model-serving environment requires the compatible base model, trained LoRA adapter, required libraries, and any necessary model-access permissions.

Follow the model-serving application's own setup instructions. Model weights are not necessarily included in the source-code repository.

**Important:** The commands above are a general setup guide. Verify the actual folder names, dependency files, environment-variable names, and startup commands before treating this section as a fully tested installation procedure.

## ⚠️ Current Limitations

- The assistant currently provides English-language responses.
- Output length is limited by the configured inference token limit.
- Model-serving availability and latency depend on the hosting environment and its resource constraints.
- The assistant can generate incorrect or incomplete information.
- Retrieval-augmented generation is not yet connected to live chat.
- No formal model-accuracy benchmark is claimed in this project description.
- The system is an informational assistant and does not replace professional aquaculture advice.

## 🔮 Future Enhancements

- Integrate retrieval-augmented generation using relevant handbook passages.
- Provide source-grounded responses and references to supporting material.
- Add Telugu and other regional-language support.
- Explore WhatsApp or mobile access.
- Conduct structured expert review of training examples.
- Introduce systematic model-quality and safety testing.
- Improve response monitoring, latency, and deployment reliability.
- Gather user feedback to guide future improvements.

## ⚖️ Disclaimer

AquaMitra AI is an educational and informational project intended to make aquaculture knowledge more accessible.

Generated responses may be inaccurate, incomplete, or unsuitable for a particular farm. They should not be treated as professional diagnoses or definitive treatment instructions. For fish mortality, suspected disease outbreaks, chemical use, or other high-impact decisions, consult qualified fisheries professionals or relevant authorities.

## 👩‍💻 Project Information

**Project:** AquaMitra AI  
**Developer:** Gayathri Sanjana Sri  
**Programme:** Veltris AI Academy  
**Focus:** Applied AI, LLM fine-tuning, full-stack development, and cloud deployment

---

*Built to explore how domain-specific Generative AI can make aquaculture information more accessible.*
