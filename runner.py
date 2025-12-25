from streamlit.web import cli as stcli
import sys

if __name__ == '__main__':
    # Эмулируем команду "streamlit run app.py"
    sys.argv = ["streamlit", "run", "app.py"]