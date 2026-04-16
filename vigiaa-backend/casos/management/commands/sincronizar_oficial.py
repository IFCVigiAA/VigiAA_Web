from django.core.management.base import BaseCommand
from django.db import connections, transaction

class Command(BaseCommand):
    help = 'Sincroniza TEMP -> OFICIAL (Bancos Separados)'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando sincronização entre bancos...")

        try:
            with connections['default'].cursor() as cursor_temp, \
                 transaction.atomic(using='oficial'):
                
                with connections['oficial'].cursor() as cursor_ofc:

                    # 1. CASOS POSITIVOS 
                    cursor_temp.execute("""
                        SELECT hash_registro, local_atendimento, inicio_sintomas, notificacao, sinan, 
                               bairro, data_nasc, observacoes, resultado, situacao, geometry,
                               aplicacao, agentes, prim_visita
                        FROM casos_positivos_temp_gl
                    """)
                    dados_pos = cursor_temp.fetchall()
                    
                    if dados_pos:
                        hashes = [d[0] for d in dados_pos]
    
                        cursor_ofc.execute("DELETE FROM casos_positivos WHERE hash_registro = ANY(%s)", [hashes])
                        
                        sql_pos = """
                            INSERT INTO casos_positivos (
                                hash_registro, local_atendimento, inicio_sintomas, notificacao, sinan, 
                                bairro, data_nasc, observacoes, resultado, situacao, geometry,
                                aplicacao, agentes, prim_visita
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        cursor_ofc.executemany(sql_pos, dados_pos)
                        self.stdout.write(f"Positivos processados: {len(dados_pos)}")

                    # 2. FOCOS
                    cursor_temp.execute("""
                        SELECT hash_registro, n_foco, localidade, imovel, deposito, tipo_atividade, 
                               data_coleta, a_aegypti_form_aquaticas, a_aegypti_form_adultas, 
                               a_albopictus_form_aquaticas, a_albopictus_form_adultas, ovo_a_aegypti, 
                               geometry
                        FROM focos_aedes_temp
                    """)
                    dados_foco = cursor_temp.fetchall()
                    if dados_foco:
                        hashes_f = [d[0] for d in dados_foco]
                        cursor_ofc.execute("DELETE FROM focos_aedes WHERE hash_registro = ANY(%s)", [hashes_f])
                        cursor_ofc.executemany("""
                            INSERT INTO focos_aedes (
                                hash_registro, n_foco, localidade, imovel, deposito, tipo_atividade, 
                                data_coleta, a_aegypti_form_aquaticas, a_aegypti_form_adultas, 
                                a_albopictus_form_aquaticas, a_albopictus_form_adultas, ovo_a_aegypti, geometry
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, dados_foco)
                        self.stdout.write(f"Focos processados: {len(dados_foco)}")

                    # 3. PONTOS ESTRATÉGICOS
                    cursor_temp.execute("""
                        SELECT hash_registro, numero, localidade, endereco, complemento, geometry
                        FROM pontos_estrategicos_temp
                    """)
                    dados_ponto = cursor_temp.fetchall()
                    if dados_ponto:
                        hashes_p = [d[0] for d in dados_ponto]
                        cursor_ofc.execute("DELETE FROM pontos_estrategicos WHERE hash_registro = ANY(%s)", [hashes_p])
                        cursor_ofc.executemany("""
                            INSERT INTO pontos_estrategicos (
                                hash_registro, numero, localidade, endereco, complemento, geometry
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                        """, dados_ponto)
                        self.stdout.write(f"Pontos processados: {len(dados_ponto)}")

                    # 4. ARMADILHAS
                    cursor_temp.execute("""
                        SELECT hash_registro, numero, localidade, complemento, tipo_imovel, tipo_armadilha, geometry
                        FROM relat_arm_temp
                    """)
                    dados_arm = cursor_temp.fetchall()
                    if dados_arm:
                        hashes_a = [d[0] for d in dados_arm]
                        cursor_ofc.execute("DELETE FROM relat_arm WHERE hash_registro = ANY(%s)", [hashes_a])
                        cursor_ofc.executemany("""
                            INSERT INTO relat_arm (
                                hash_registro, numero, localidade, complemento, tipo_imovel, tipo_armadilha, geometry
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, dados_arm)
                        self.stdout.write(f"Armadilhas processadas: {len(dados_arm)}")

            self.stdout.write(self.style.SUCCESS("✅ SINCRONIZAÇÃO REAL CONCLUÍDA"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro na sincronização: {str(e)}"))
            raise e