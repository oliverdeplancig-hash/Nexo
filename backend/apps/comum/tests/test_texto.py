from apps.comum import texto


def test_normalizar_remove_acentos_pontuacao_e_espacos():
    assert texto.normalizar("  Solicitação   de FÉRIAS!! ") == "solicitacao de ferias"


def test_tokens_unificam_flexoes():
    assert texto.tokens("Como solicito férias?") == texto.tokens("Como faço para solicitar minhas férias?")
    assert texto.tokens("documentos") == texto.tokens("documento")


def test_tokens_sao_deterministicos():
    frase = "Quais documentos preciso apresentar para a licença?"
    assert all(texto.tokens(frase) == texto.tokens(frase) for _ in range(50))


def test_dice_e_cobertura():
    assert texto.dice(["a", "b"], ["a", "b"]) == 1.0
    assert texto.dice([], ["a"]) == 0.0
    assert texto.cobertura(["a", "b"], ["a", "c"]) == 0.5
