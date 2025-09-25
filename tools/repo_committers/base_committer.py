from typing import Dict, Any, List

class BaseCommitter:
    
    @staticmethod
    def _inicializar_resultado_branch(nome_branch: str) -> Dict[str, Any]:
        return {
            "branch_name": nome_branch,
            "success": False,
            "pr_url": None,
            "message": "",
            "arquivos_modificados": []
        }
    
    @staticmethod
    def _processar_mudancas_comuns(conjunto_de_mudancas: list, resultado_branch: Dict[str, Any]) -> List[Dict[str, Any]]:
        mudancas_validas = []
        
        for mudanca in conjunto_de_mudancas:
            caminho = mudanca.get("caminho_do_arquivo")
            status = mudanca.get("status", "").upper()
            conteudo = mudanca.get("conteudo")
            
            if not caminho:
                print("  [AVISO] Mudança ignorada por não ter 'caminho_do_arquivo'.")
                continue
            
            mudancas_validas.append({
                "caminho": caminho,
                "status": status,
                "conteudo": conteudo,
                "justificativa": mudanca.get("justificativa", f"Aplicando mudança em {caminho}")
            })
            
            resultado_branch["arquivos_modificados"].append(caminho)
        
        return mudancas_validas
    
    @staticmethod
    def _finalizar_resultado_sucesso(resultado_branch: Dict[str, Any], pr_url: str = None, message: str = "PR criado.") -> None:
        resultado_branch.update({
            "success": True,
            "pr_url": pr_url,
            "message": message
        })
    
    @staticmethod
    def _finalizar_resultado_erro(resultado_branch: Dict[str, Any], error_message: str) -> None:
        resultado_branch["message"] = error_message