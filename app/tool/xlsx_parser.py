from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import io
import os
import json
import re
from pydantic import BaseModel, Field


class BaseTool(ABC, BaseModel):
    name: str
    description: str
    parameters: Optional[dict] = None

    class Config:
        arbitrary_types_allowed = True

    async def __call__(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        return await self.execute(**kwargs)

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""

    def to_param(self) -> Dict:
        """Convert tool to function call format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolResult(BaseModel):
    """Represents the result of a tool execution."""

    output: Any = Field(default=None)
    error: Optional[str] = Field(default=None)
    system: Optional[str] = Field(default=None)

    class Config:
        arbitrary_types_allowed = True

    def __bool__(self):
        return any(getattr(self, field) for field in self.__fields__)

    def __add__(self, other: "ToolResult"):
        def combine_fields(
            field: Optional[str], other_field: Optional[str], concatenate: bool = True
        ):
            if field and other_field:
                if concatenate:
                    return field + other_field
                raise ValueError("Cannot combine tool results")
            return field or other_field

        return ToolResult(
            output=combine_fields(self.output, other.output),
            error=combine_fields(self.error, other.error),
            system=combine_fields(self.system, other.system),
        )

    def __str__(self):
        return f"Error: {self.error}" if self.error else self.output

    def replace(self, **kwargs):
        """Returns a new ToolResult with the given fields replaced."""
        # return self.copy(update=kwargs)
        return type(self)(**{**self.dict(), **kwargs})


class CLIResult(ToolResult):
    """A ToolResult that can be rendered as a CLI output."""


class ToolFailure(ToolResult):
    """A ToolResult that represents a failure."""


class AgentAwareTool:
    agent: Optional = None


class ExcelDataExtractor(BaseTool, AgentAwareTool):
    name: str = "excel_data_extractor"
    description: str = "Extracts data from Excel files. Can read sheets, specific ranges, or entire files."
    parameters: Dict = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the Excel file to extract data from"
            },
            "sheet_name": {
                "type": "string",
                "description": "Name of the sheet to extract data from. If not provided, will use the first sheet.",
                "default": None
            },
            "range": {
                "type": "string",
                "description": "Range to extract in Excel notation (e.g., 'A1:C10'). If not provided, extracts the entire sheet.",
                "default": None
            },
            "header_row": {
                "type": "integer",
                "description": "Row to use as header (0-based index). Default is 0.",
                "default": 0
            },
            "output_format": {
                "type": "string", 
                "enum": ["json", "csv", "dict", "dataframe"],
                "description": "Format to return the data in (json, csv, dict, dataframe). Default is json.",
                "default": "json"
            },
            "clean_column_names": {
                "type": "boolean",
                "description": "Whether to clean column names by removing leading/trailing spaces and normalizing unicode characters.",
                "default": True
            }
        },
        "required": ["file_path"]
    }

    async def execute(self, 
                     file_path: str,
                     sheet_name: Optional[str] = None,
                     range: Optional[str] = None,
                     header_row: int = 0,
                     output_format: str = "json",
                     clean_column_names: bool = True) -> ToolResult:
        """
        Extract data from an Excel file.
        
        Args:
            file_path: Path to the Excel file
            sheet_name: Name of the sheet to extract (default: first sheet)
            range: Cell range to extract (e.g., 'A1:C10')
            header_row: Row to use as header (0-based index)
            output_format: Format to return data (json, csv, dict, dataframe)
            clean_column_names: Whether to clean column names
            
        Returns:
            ToolResult with the extracted data or error
        """
        try:
            if not os.path.exists(file_path):
                return ToolFailure(error=f"File not found: {file_path}")
            
            read_params = {"header": header_row}
            
            if range:
                try:
                    cells = range.split(":")
                    if len(cells) != 2:
                        return ToolFailure(error=f"Invalid range format: {range}. Expected format like 'A1:C10'")
                        
                    read_params["usecols"] = range
                except Exception as e:
                    return ToolFailure(error=f"Error parsing range '{range}': {str(e)}")
            
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name, **read_params)
            else:
                df = pd.read_excel(file_path, **read_params)
                
            if clean_column_names:
                df.columns = [col.strip() if isinstance(col, str) else col for col in df.columns]
                
                rename_map = {}
                for col in df.columns:
                    if isinstance(col, str):
                        new_col = col.strip()
                        rename_map[col] = new_col
                
                df = df.rename(columns=rename_map)
            
            if output_format.lower() == "json":
                json_str = df.to_json(orient="records", force_ascii=False)
                result = json_str
            elif output_format.lower() == "csv":
                result = df.to_csv(index=False)
            elif output_format.lower() == "dict":
                result = df.to_dict(orient="records")
            elif output_format.lower() == "dataframe":
                result = df
            else:
                return ToolFailure(error=f"Invalid output format: {output_format}")
                
            return ToolResult(
                output=result,
                system=f"Successfully extracted data from {file_path}" + 
                       (f", sheet '{sheet_name}'" if sheet_name else "") +
                       (f", range {range}" if range else "")
            )
            
        except Exception as e:
            return ToolFailure(
                error=f"Error extracting data from Excel file: {str(e)}"
            )

