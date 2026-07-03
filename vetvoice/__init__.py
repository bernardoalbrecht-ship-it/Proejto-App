"""
VetVoice — sistema de atendimento veterinário por voz.

Organizado em Clean Architecture, com dependências apontando SEMPRE para
dentro (presentation -> application -> domain; infrastructure implementa as
portas do domínio):

    shared          -> configuração/constantes compartilhadas
    domain          -> entidades e regras de negócio (parser híbrido, portas)
    application     -> casos de uso (orquestração)
    infrastructure  -> implementações concretas (SQLite, Google, áudio, GPT)
    presentation    -> interface Kivy (Windows/Android)
    composition     -> "composition root": monta as dependências reais

Nenhuma regra de negócio vive na interface; nenhum detalhe de framework vive
no domínio.
"""

__version__ = "2.0.0"
