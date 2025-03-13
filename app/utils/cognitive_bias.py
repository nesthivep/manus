"""Utility for detecting and mitigating cognitive biases based on 'Thinking Fast and Slow'."""

from typing import Dict, List, Optional, Callable
from pydantic import BaseModel, Field

from app.logger import logger


class BiasDefinition(BaseModel):
    """Definition of a cognitive bias with detection and mitigation strategies."""
    
    name: str
    description: str
    detection_patterns: List[str] = Field(default_factory=list)
    
    def detect(self, text: str) -> bool:
        """Detect if the bias is present in the text."""
        return any(pattern.lower() in text.lower() for pattern in self.detection_patterns)


class CognitiveBiasMitigation:
    """System to detect and mitigate cognitive biases in agent reasoning."""
    
    def __init__(self):
        self.biases = self._initialize_biases()
    
    def _initialize_biases(self) -> Dict[str, BiasDefinition]:
        """Initialize the catalog of cognitive biases from 'Thinking Fast and Slow'."""
        return {
            "anchoring_bias": BiasDefinition(
                name="Anchoring Bias",
                description="Tendency to rely too heavily on the first piece of information encountered",
                detection_patterns=[
                    "based on the initial", 
                    "starting with the given", 
                    "first value mentioned"
                ]
            ),
            "availability_bias": BiasDefinition(
                name="Availability Bias",
                description="Tendency to overestimate likelihood of events based on their availability in memory",
                detection_patterns=[
                    "commonly known examples", 
                    "recent cases", 
                    "easily recalled", 
                    "popular examples"
                ]
            ),
            "loss_aversion": BiasDefinition(
                name="Loss Aversion",
                description="Tendency to prefer avoiding losses over acquiring equivalent gains",
                detection_patterns=[
                    "avoid losing", 
                    "prevent loss", 
                    "too risky", 
                    "better safe than sorry"
                ]
            ),
            "overconfidence": BiasDefinition(
                name="Overconfidence Bias",
                description="Tendency to overestimate one's abilities or knowledge",
                detection_patterns=[
                    "certainly", 
                    "definitely", 
                    "absolutely", 
                    "no doubt", 
                    "guaranteed"
                ]
            ),
            "framing_effect": BiasDefinition(
                name="Framing Effect",
                description="Drawing different conclusions based on how information is presented",
                detection_patterns=[
                    "considering only the positive", 
                    "focusing on the negative", 
                    "viewed from the perspective of"
                ]
            ),
        }
    
    def check_for_biases(self, text: str) -> List[str]:
        """Identify potential biases in text."""
        detected_biases = []
        for bias_id, bias in self.biases.items():
            if bias.detect(text):
                detected_biases.append(bias_id)
                logger.info(f"Detected potential {bias.name} in reasoning")
        return detected_biases
    
    def get_mitigation_prompts(self, detected_biases: List[str]) -> List[str]:
        """Generate prompts to mitigate the detected biases."""
        mitigation_prompts = []
        
        for bias_id in detected_biases:
            if bias_id not in self.biases:
                continue
                
            bias = self.biases[bias_id]
            
            if bias_id == "anchoring_bias":
                mitigation_prompts.append(
                    "Consider a different starting point or reference. What would your approach be "
                    "if you had different initial information?"
                )
            elif bias_id == "availability_bias":
                mitigation_prompts.append(
                    "Consider less common examples that don't immediately come to mind. "
                    "Are there alternative scenarios that may be relevant?"
                )
            elif bias_id == "loss_aversion":
                mitigation_prompts.append(
                    "Consider both the potential gains and losses equally. "
                    "Try reframing the situation in terms of opportunities rather than risks."
                )
            elif bias_id == "overconfidence":
                mitigation_prompts.append(
                    "Consider the limitations of your knowledge. "
                    "What are some reasons your conclusion might be wrong?"
                )
            elif bias_id == "framing_effect":
                mitigation_prompts.append(
                    "Try reframing the problem from multiple perspectives. "
                    "How would your approach change if this were presented differently?"
                )
        
        return mitigation_prompts 