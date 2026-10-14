# Enubox: Mattermost — A Plataforma de Colaboração Que Falou Demais

Bora rapaziada!! Quem diria que uma plataforma de mensagens corporativas ia vazar as próprias credenciais em cadeia? Enubox: Mattermost é um puzzle belissimamente encadeado: TFTP vaza creds do admin, o plugin Zoom do Mattermost vaza creds do FTP, o FTP vaza a senha do SSH, e um binário customizado com uma chave hex hardcoded te pede pra provar que você sabe abrir o Ghidra. Quatro serviços, quatro pivots, uma root. Design absurdamente top demais, sem mentira.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | Enubox: Mattermost |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/enubox-mattermost,414/ |
| **Técnicas** | nmap UDP/TCP, TFTP anônimo, painel admin Mattermost, vazamento de credencial via plugin, FTP, RE de binário com Ghidra (constante hex) |
| **CVEs** | CWE-200 (Exposição de informação via TFTP), CWE-522 (Credenciais mal protegidas em config de plugin), CWE-798 (Credenciais hardcoded em binário) |
| **Grupos APT** | APT41: usa vazamento de credenciais de plataformas colaborativas para acesso inicial em intrusões corporativas; FIN7: pivota por serviços de transferência de arquivos mal configurados |

---

## Resumo do Ataque

```
nmap -sT -sU → TFTP/69, FTP/21, SSH/22, HTTP/80, Mattermost/8065
  → TFTP anônimo: get README.md → admin:ComplexPassword0!
  → Login Mattermost :8065 → Console do Sistema → plugin Zoom
  → alterar URL da API Zoom para o alvo → resposta vaza creds FTP
  → FTP ftpuser:ftppassword → /users/mattermost/message → senha SSH "Welcome!!"
  → SSH mattermost@alvo → binário Desktop/secret
  → transferir binário → Ghidra decompila main()
  → constante hex 0xf447 → decimal 62535
  → ./secret → inserir 62535 → uid=0(root)
  → /root/Desktop/local.txt
```

---

## Metodologia

1. Scan TCP + UDP completo para encontrar TFTP (UDP/69) além dos serviços padrão
2. Leitura anônima via TFTP do README.md para obter credenciais admin do Mattermost
3. Painel admin Mattermost: habilitar plugin Zoom, manipular URL da API para acionar vazamento de credencial
4. Login FTP com credenciais vazadas, recuperar senha SSH do arquivo de mensagem
5. SSH como mattermost, enumerar Desktop
6. Transferir binário customizado para o atacante, decompilar com Ghidra
7. Extrair chave hex de main(), converter para decimal, fornecer ao binário, obter shell root

---

## Passo 1 — Descoberta de Host e Scan Completo de Portas

```bash
sudo netdiscover -r 192.168.0.0/24
# Alvo: 192.168.0.110

nmap -sT -sU -A -p- 192.168.0.110
```

```
PORT     STATE SERVICE  VERSION
21/tcp   open  ftp      vsftpd 3.0.3
22/tcp   open  ssh      OpenSSH 7.x
80/tcp   open  http     Apache httpd 2.4.x
8065/tcp open  http     Mattermost
69/udp   open  tftp     TFTP
```

Cinco serviços, superfície de ataque bem generosa. TFTP em UDP é fácil de perder sem o `-sU`. Começar pelo TFTP.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Leitura Anônima via TFTP

TFTP não tem autenticação por padrão. Qualquer arquivo na raiz do TFTP é legível por qualquer um:

```bash
tftp 192.168.0.110
tftp> get README.md
tftp> quit
cat README.md
```

```
Credenciais admin do Mattermost
Username: admin
Password: ComplexPassword0!
```

Credenciais num arquivo acessível via TFTP. Caramba, isso é surreal. É exatamente assim que configurações erradas de TFTP funcionam no mundo real.

**Nota do mundo real:** TFTP ainda é usado para PXE boot, entrega de firmware de dispositivos de rede e configuração de telefones IP. Expor sem filtro de IP é um achado crítico em qualquer auditoria corporativa.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1552.001 — Credenciais em Arquivos

---

## Passo 3 — Painel Admin Mattermost: Vazamento via Plugin Zoom

Navegar para `http://192.168.0.110:8065/login`. Logar como `admin` / `ComplexPassword0!`.

Ir em: **Console do Sistema > Plugins > Zoom**. Habilitar o plugin. Abrir configuração. Alterar a URL da API Zoom de `localhost` para o IP do alvo. Salvar.

O plugin tenta um callback e a resposta de erro vaza as credenciais FTP configuradas no backend:

```
FTP User: ftpuser
FTP Pass: ftppassword
```

**Por que isso acontece?** Integrações de plugin que ecoam credenciais de serviços backend em respostas de erro de API são uma misconfiguration clássica. A URL do callback acionou um código path inesperado que jogou as creds FTP na UI admin.

**MITRE ATT&CK:** T1078.001 — Contas Válidas: Contas Padrão; T1552.001 — Credenciais em Arquivos

---

## Passo 4 — Acesso FTP: Recuperar Senha SSH

```bash
ftp 192.168.0.110
Name: ftpuser
Password: ftppassword
ftp> ls -la
ftp> cd users/mattermost
ftp> get message
ftp> bye
cat message
```

```
Caro mattermost,
Sua senha SSH temporária é: Welcome!!
```

Cadeia de credenciais completa: TFTP → Mattermost admin → FTP → senha SSH.

**MITRE ATT&CK:** T1021.003 — Serviços Remotos: FTP; T1552.001 — Credenciais em Arquivos

---

## Passo 5 — Acesso SSH e Descoberta do Binário

```bash
ssh mattermost@192.168.0.110
# Senha: Welcome!!

ls
cd Desktop/
ls -la
cat README.md
./secret
```

O `README.md` do Desktop contém uma chave que parece funcionar, mas o binário retorna "expirado." Precisa de análise de engenharia reversa.

Transferir para a máquina do atacante:

```bash
# No alvo (iniciar servidor HTTP)
python3 -m http.server 8080

# No atacante
wget http://192.168.0.110:8080/secret
chmod +x secret
```

**MITRE ATT&CK:** T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 6 — Engenharia Reversa do Binário com Ghidra

Abrir o binário no Ghidra. Criar novo projeto, importar `secret`, deixar análise automática rodar, abrir o **CodeBrowser**.

Navegar para `main()` na visão do decompiler. A função lê input do usuário e compara com uma constante hexadecimal:

```c
if (input == 0xf447) {
    // spawna shell
}
```

Converter hex para decimal:

```bash
python3 -c "print(0xf447)"
# 62535
```

**Alternativa (sem Ghidra):** usar radare2:

```bash
r2 secret
[0x00400550]> aaa
[0x00400550]> pdf @ main
# Procurar a instrução CMP e o operando
```

**MITRE ATT&CK:** T1027 — Arquivos e Informações Ofuscadas

---

## Passo 7 — Shell Root via Chave do Binário

```bash
./secret
Enter key: 62535

whoami
# root

cd /root/Desktop
cat local.txt
```

Root obtido. O binário era SUID e spawnou shell root com a chave correta.

**MITRE ATT&CK:** T1548.001 — Mecanismo de Controle de Elevação: Setuid

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Usado Para |
|---|---|---|---|
| Credencial | admin:ComplexPassword0! | TFTP README.md | Login admin Mattermost |
| Credencial | ftpuser:ftppassword | Vazamento plugin Zoom/Mattermost | Login FTP |
| Credencial | mattermost:Welcome!! | FTP /users/mattermost/message | Login SSH |
| Chave binária | 62535 (0xf447) | Ghidra decompile do binário `secret` | Shell root |
| Flag root | local.txt | /root/Desktop/local.txt | Capturada |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Conclusão |
|---|---|---|---|
| 1 | TFTP expõe credenciais em arquivo de leitura anônima | TFTP ainda roda em milhares de redes corporativas para PXE boot e config VOIP | Desabilitar TFTP ou restringir por IP; nunca armazenar credenciais em paths acessíveis via TFTP |
| 2 | Plugin de plataforma colaborativa vaza credenciais de serviço downstream em resposta de erro | Plataformas SaaS com ecossistemas de plugins expõem credenciais regularmente via callbacks mal configurados | Sanitizar todas as respostas de configuração de plugin |
| 3 | Cadeia de credenciais: TFTP → Mattermost → FTP → SSH | Intrusões APT reais encadeiam três ou quatro pivots de credenciais entre serviços | Segmentar armazenamento de credenciais; rotacionar independentemente por serviço |
| 4 | Chave numérica hardcoded em binário SUID | Desenvolvedores embarcam verificações de "segurança" em binários assumindo que usuários não conseguem fazer RE | Nunca usar segredos hardcoded para elevação de privilégio |
| 5 | Python3 HTTP server para transferência de binário | Ferramentas legítimas nativas viabilizam transferência de arquivos sem instalar software adicional | Monitorar serviços HTTP ad-hoc em endpoints (T1105) |

---

## MITRE ATT&CK

| Fase | Tática | Técnica | ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso a Credenciais | Credenciais em Arquivos (TFTP) | T1552.001 |
| Acesso Inicial | Acesso Inicial | Contas Válidas: Contas Padrão | T1078.001 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: FTP | T1021.003 |
| Execução | Execução | Interpretador de Comandos: Unix Shell | T1059.004 |
| Evasão de Defesa | Evasão de Defesa | Arquivos e Informações Ofuscadas | T1027 |
| Escalação de Privilégio | Escalação de Privilégio | Mecanismo de Controle de Elevação: Setuid | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Desabilitar TFTP ou restringir por IP** — nunca acessível de estações de trabalho; nunca armazenar credenciais no root TFTP
2. **Sanitizar respostas de configuração de plugins** — credenciais nunca devem aparecer em saída de erro de API
3. **Rotacionar credenciais por serviço** — cada serviço deve usar credenciais independentes
4. **Remover SUID do binário customizado** — usar sudo com allowlist específica; nunca embarcado chaves em binários SUID
5. **Autenticação SSH por chave** — desabilitar autenticação por senha no sshd\_config

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todos os serviços TFTP e FTP; documentar controles de acesso |
| Proteger | Controle de Acesso | Restringir TFTP à VLAN de gerenciamento; desabilitar FTP anônimo |
| Proteger | Segurança de Dados | Remover credenciais de arquivos TFTP; sanitizar respostas de plugin |
| Detectar | Anomalias e Eventos | Alertar em leituras TFTP, logins FTP e servidores HTTP ad-hoc |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais da cadeia; desabilitar TFTP e FTP desnecessários |
| Recuperar | Planejamento de Recuperação | Auditar todos os binários SUID; reconstruir host comprometido |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Controle de Acesso | Restringir TFTP e FTP a hosts autorizados |
| AC-6 | Mínimo Privilégio | Remover SUID de binários não essenciais |
| IA-5 | Gerenciamento de Autenticadores | Rotacionar credenciais; não reutilizar entre serviços |
| SC-28 | Proteção de Informação em Repouso | Sem credenciais em arquivos acessíveis via TFTP |
| CM-7 | Funcionalidade Mínima | Desabilitar TFTP se não necessário; restringir FTP |
| SA-11 | Testes de Segurança no Desenvolvimento | Revisão de código para segredos hardcoded em binários |

### CISA KEV

O padrão de acesso anônimo TFTP e o vazamento de credencial em resposta de plugin mapeiam para padrões documentados no CISA Alert AA22-074A (uso de serviços mal configurados para acesso inicial por atores de ameaça).

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL2 |
| Gestão de Ativos, Mudanças e Configurações (ASSET) | Gerenciar Inventário de Ativos de TI | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (sanitizar respostas de plugin; restringir TFTP)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (auditar binários SUID; restringir sudo)
- **D3-NTF** — Filtragem de Tráfego de Rede (bloquear TFTP de segmentos de estações de trabalho)

---

## Considerações Finais

Mano, Enubox: Mattermost é uma aula magistral de encadeamento de credenciais. Cada serviço te entrega a chave do próximo, e o passo de RE de binário no final é uma ótima introdução ao Ghidra para quem nunca fez engenharia reversa. A lição é real: plataformas de colaboração, ferramentas de mensagem e seus ecossistemas de plugin são superfícies de ataque cada vez mais valiosas em ambientes corporativos. APT41 e FIN7 já exploraram configurações similares em intrusões reais. Top demais essa máquina, véi, sem exagero.

Thanks guys!! (❍ᴥ❍ʋ)
