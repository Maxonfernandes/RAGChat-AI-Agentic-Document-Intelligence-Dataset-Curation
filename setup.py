from setuptools import setup, find_packages

setup(
    name="ragchat",
    version="1.0.0",
    description="Agentic RAG Multi-Agent Document Intelligence & Dataset Curation",
    author="Maxon Fernandes, Arshith Vaz, Janice Dsouza, Kaavya Rao",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "fastapi>=0.110.0",
        "uvicorn[standard]>=0.28.0",
        "pydantic>=2.6.0",
        "python-dotenv>=1.0.0",
        "google-generativeai>=0.8.0",
        "astrapy>=2.0.0",
        "pypdf>=4.0.0",
        "pillow>=10.0.0",
        "requests>=2.31.0",
        "httpx>=0.27.0",
        "python-multipart>=0.0.9",
        "numpy>=1.26.0",
    ],
)
