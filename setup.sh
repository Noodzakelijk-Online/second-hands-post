#bash
echo $$ > /tmp/setup.lock

# Check if the venv directory exists
if [ ! -d "/home/noodzalijkonline/python_bot/venv" ]; then
    # Create a Python virtual environment named 'venv' if it doesn't exist
    python3 -m venv /home/noodzakelijkonline/python_bot/venv
    echo "Created a new virtual environment named 'venv'."
else
    echo "Virtual environment 'venv' already exists."
fi

echo "Activating the virtual environment..."
# Activate the virtual environment
source /home/noodzakelijkonline/python_bot/venv/bin/activate

echo "Installing packages from requirements.txt..."
# Install packages from requirements.txt



# Check if the NLP processing data 'nl_core_news_md' already exists
if ! python -m spacy info nl_core_news_md > /dev/null 2>&1; then
    echo "Downloading NLP processing data 'nl_core_news_md'..."
    python -m spacy download nl_core_news_md
else
    echo "NLP processing data 'nl_core_news_md' already exists."
fi

echo "Running the main.py file..."
# Run the main.py file
python /home/noodzakelijkonline/python_bot/main.py

rm /tmp/setup.lock