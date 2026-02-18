# ERIS Stakeholder Presentation

## Generate the PowerPoint

1. Install the dependency (if not already installed):
   ```bash
   pip install python-pptx
   ```

2. From the **project root**, run:
   ```bash
   python scripts/create_stakeholder_presentation.py
   ```

3. Open the generated file:
   - **ERIS_Stakeholder_Presentation.pptx** (in the project root)

## Contents (20 slides)

- Title & agenda  
- Project introduction & business objectives  
- Solution overview (pipeline phases)  
- Data sources (NewsAPI, Fed, Market, Kaggle, Earnings)  
- Data pipeline order  
- Feature engineering: preprocessing & market  
- Models: FinBERT (sentiment), HMM (regime), BERTopic (topics)  
- Stress level & KPI dashboard  
- AI briefing & mitigation paths  
- End-to-end flow  
- Technical terminology (glossary + business significance)  
- KPI success factors  
- Conclusion (industry relevance)  
- Thank you

You can edit the `.pptx` in PowerPoint to add your logo, branding, or speaker notes.
