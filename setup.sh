#bash

# Check if the venv directory exists
if [ ! -d "venv" ]; then
    # Create a Python virtual environment named 'venv' if it doesn't exist
    python3 -m venv venv
    echo "Created a new virtual environment named 'venv'."
else
    echo "Virtual environment 'venv' already exists."
fi

# Activate the virtual environment
source venv/bin/activate

# Install packages from requirements.txt
pip install -r requirements.txt

# Download the NLP processing data
python -m spacy download nl_core_news_md

# Run the main.py file
python main.py