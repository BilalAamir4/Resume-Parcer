"""
regex_patterns.py
All compiled regex patterns and keyword lists for the resume extraction pipeline.
"""

import re

# ─── Contact Info Patterns ────────────────────────────────────────────────────

EMAIL = re.compile(
    r'[\w\.-]+@[\w\.-]+\.\w+'
)

PHONE = re.compile(
    r'(\+?\d{1,3}[\s\-]?)?'
    r'(\(?\d{2,4}\)?[\s\-]?)'
    r'(\d{3,4}[\s\-]?\d{3,4})'
)

LINKEDIN = re.compile(
    r'(?:(?:https?://)?(?:www\.)?linkedin\.com/in/|/in/)[\w\-]+',
    re.IGNORECASE
)

GITHUB = re.compile(
    r'(?:https?://)?(?:www\.)?github\.com/[\w\-]+',
    re.IGNORECASE
)

LINKEDIN_USERNAME = re.compile(
    r'(?:linkedin\.com/in/|ï\s*)([\w\-]+)',
    re.IGNORECASE
)

GITHUB_USERNAME = re.compile(
    r'(?:github\.com/|§\s*)([\w\-]+)',
    re.IGNORECASE
)

# ─── Education Patterns ───────────────────────────────────────────────────────

GRADUATION_YEAR = re.compile(
    r'\b(19[89]\d|20[0-3]\d)\b'
)

# ─── Skills Keywords (120+ entries) ──────────────────────────────────────────

SKILLS_KEYWORDS = [
    # Programming Languages
    "Python", "Java", "C", "C++", "C#", "JavaScript", "TypeScript", "PHP",
    "Ruby", "Swift", "Kotlin", "Go", "Rust", "R", "MATLAB", "Scala", "Perl",
    "SQL", "HTML", "CSS", "Bash", "Shell", "PowerShell", "Dart", "Elixir",
    "Haskell", "Clojure", "Groovy", "Assembly", "COBOL", "Fortran", "Lua",

    # Web Frameworks & Libraries
    "React", "Angular", "Vue", "Node.js", "Django", "Flask", "FastAPI",
    "Spring", "Laravel", "Express", "Next.js", "Nuxt.js", "Svelte",
    "Bootstrap", "jQuery", "Tailwind", "Ruby on Rails", "ASP.NET",

    # AI / ML / Data Science
    "TensorFlow", "PyTorch", "Keras", "Scikit-learn", "Pandas", "NumPy",
    "OpenCV", "Machine Learning", "Deep Learning", "NLP",
    "Computer Vision", "Reinforcement Learning", "Data Science",
    "Data Analysis", "Data Engineering", "Statistics", "Matplotlib",
    "Seaborn", "SciPy", "XGBoost", "LightGBM", "BERT", "Transformers",
    "OpenAI", "LangChain", "Hugging Face", "YOLOv8", "Streamlit",

    # Databases
    "MySQL", "PostgreSQL", "MongoDB", "Redis", "SQLite", "Oracle",
    "Cassandra", "DynamoDB", "Elasticsearch", "MariaDB", "Neo4j",
    "InfluxDB", "CouchDB", "Firebase",

    # Cloud & DevOps
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Ansible",
    "Jenkins", "CI/CD", "DevOps", "Linux", "Windows", "Ubuntu", "Nginx",
    "Apache", "Heroku", "Vercel", "Netlify", "CloudFormation",

    # Tools & Platforms
    "Git", "GitHub", "GitLab", "Bitbucket", "JIRA", "Confluence",
    "Postman", "Selenium", "Pytest", "JUnit", "REST", "GraphQL",
    "Tableau", "Power BI", "Excel", "Agile", "Scrum", "Kanban",

    # Mobile Development
    "Android", "iOS", "Flutter", "React Native", "Xamarin",

    # Big Data
    "Hadoop", "Spark", "Kafka", "Hive", "Pig", "Flink", "Airflow",

    # Other Tech
    "Blockchain", "Unity", "Unreal Engine", "WebSocket", "gRPC",
    "Microservices", "SOA", "OAuth", "JWT", "OpenAPI", "Swagger",
    "RabbitMQ", "Celery", "Redis Queues",
]

# ─── Degree Keywords ──────────────────────────────────────────────────────────

DEGREE_KEYWORDS = [
    "B.E", "B.Tech", "B.Sc", "B.S", "B.A", "B.Com", "BCA", "BBA",
    "M.E", "M.Tech", "M.Sc", "M.S", "M.A", "MBA", "MCA", "M.Com",
    "Ph.D", "PhD", "Doctorate", "Diploma", "PG-DAC", "PGDM",
    "Bachelor", "Master", "Associate", "HSC", "SSC",
]
