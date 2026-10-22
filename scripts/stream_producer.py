"""PDF-compatible native-streaming entrypoint; invoke from the project root."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hospital.streaming import main

if __name__=='__main__':
    main()
