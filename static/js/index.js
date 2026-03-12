document.addEventListener('DOMContentLoaded', () => {

    const weightTolerances = {
        'BRANCO 110G': {'18X30X10':{min:25.52,max:29.02},'22X30X12':{min:30.80,max:34.06},'22X40X12':{min:38.50,max:41.50},'32X30X12':{min:39.60,max:45.60},'32X40X12':{min:49.50,max:56.50},'35X45X14':{min:59.90,max:66.90},'32X45X12':{min:55.44,max:61.74},'32X30X16':{min:43.56,max:47.56},'28X31X20':{min:49.01,max:53.01},'32X45X16':{min:59.90,max:65.90},'25X30X9':{min:30.80,max:34.30},'18X25X10':{min:22.33,max:26.63},'25X25X9':{min:26.95,max:31.25},'29X40X15':{min:49.50,max:53.80},'25X40X14':{min:44.00,max:48.30},'25X30X14':{min:35.20,max:39.50},'40X45X14':{min:66.55,max:73.55},'31X31X18':{min:49.01,max:55.01},'25X30X14':{min:35.20,max:39.50}},
        'BAG 100GRS': {'18X30X10':{min:23.20,max:26.70},'22X30X12':{min:28.00,max:31.26},'22X40X12':{min:35.00,max:38.00},'32X30X12':{min:36.00,max:42.00},'32X40X12':{min:45.00,max:52.00},'35X45X14':{min:54.45,max:61.45},'32X45X12':{min:50.40,max:56.70},'32X30X16':{min:39.60,max:43.60},'28X31X20':{min:44.55,max:48.55},'32X45X16':{min:54.45,max:60.45},'25X30X9':{min:28.00,max:31.50},'18X25X10':{min:20.30,max:24.60},'25X25X9':{min:24.50,max:28.80},'29X40X15':{min:45.00,max:49.30},'25X40X14':{min:40.00,max:44.30},'25X30X14':{min:32.00,max:36.30},'40X45X14':{min:60.50,max:67.50},'31X31X18':{min:44.55,max:50.55},'25X30X14':{min:32.00,max:36.30}},
        'BAG 80GRS': {'18X30X10':{min:18.56,max:22.06},'22X30X12':{min:22.40,max:25.66},'22X40X12':{min:28.00,max:31.00},'32X30X12':{min:28.80,max:34.80},'32X40X12':{min:36.00,max:43.00},'35X45X14':{min:43.56,max:50.56},'32X45X12':{min:40.32,max:46.62},'32X30X16':{min:31.68,max:35.68},'28X31X20':{min:35.64,max:39.64},'32X45X16':{min:43.56,max:49.56},'25X30X9':{min:22.40,max:25.90},'18X25X10':{min:16.24,max:20.54},'25X25X9':{min:19.60,max:23.90},'29X40X15':{min:36.00,max:40.30},'25X40X14':{min:32.00,max:36.30},'25X30X14':{min:25.60,max:29.90},'40X45X14':{min:48.40,max:55.40},'31X31X18':{min:35.64,max:41.64},'25X30X14':{min:25.60,max:29.90}},
        'BAG 70GRS': {'18X30X10':{min:16.24,max:19.74},'22X30X12':{min:19.60,max:22.86},'22X40X12':{min:24.50,max:27.50},'32X30X12':{min:25.20,max:31.20},'32X40X12':{min:31.50,max:38.50},'35X45X14':{min:38.12,max:45.12},'32X45X12':{min:35.28,max:41.58},'32X30X16':{min:27.72,max:31.72},'28X31X20':{min:31.19,max:35.19},'32X45X16':{min:38.12,max:44.12},'25X30X9':{min:19.60,max:23.10},'18X25X10':{min:14.21,max:18.51},'25X25X9':{min:17.15,max:21.45},'29X40X15':{min:31.50,max:35.80},'25X40X14':{min:28.00,max:32.30},'25X30X14':{min:22.40,max:26.70},'40X45X14':{min:42.35,max:49.35},'31X31X18':{min:31.19,max:37.19},'25X30X14':{min:22.40,max:26.70}}
    };
    weightTolerances['COLLEY 100G'] = weightTolerances['BAG 100GRS'];
    weightTolerances['ECO 70GRS'] = weightTolerances['BAG 70GRS'];
    weightTolerances['MONOL 70GR'] = weightTolerances['BAG 70GRS'];
    
    const IDEAL_SPEED_RATES={'18X30X10':4100,'22X30X12':4100,'22X40X12':3900,'32X30X12':4000,'32X40X12':3600,'35X45X14':3200,'32X45X12':3200,'32X30X16':3300,'28X31X20':3200,'32X45X16':3200,'25X30X9':3900,'18X25X10':4100,'25X25X9':3700,'29X40X15':3700,'25X40X14':3900,'25X30X14':4000,'40X45X14':3000,'31X31X18':3700,'31X31X16':3700};
    const IDEAL_SETUP_TIMES_MIN={1:15.0,2:22.5,3:32.5};
    const IDEAL_SCRAP_RATES_SOS_PCT={'BRANCO 110G':8.0,'BAG 100GRS':6.0,'BAG 80GRS':6.0,'BAG 70GRS':8.0,'COLLEY 100G':8.0,'ECO 70GRS':10.0,'MONOL 70GRS':10.0};
    
    function getSeconds(t){if(!t)return 0;const[h,m]=t.split(':').map(Number);return(h*3600)+(m*60);}

    function validateMilheiro() {
        const milheiroInput = document.querySelector('[name=milheiro]');
        const milheiroValue = parseFloat(milheiroInput.value);
        if (!milheiroValue) return;

        const formato = document.querySelector('[name=formato]').value;
        const papel = document.querySelector('[name=papel]').value;

        const tolerance = weightTolerances[papel] ? weightTolerances[papel][formato] : null;

        if (tolerance) {
            // Substituído alert() por um console.warn() para evitar pop-ups no navegador
            if (milheiroValue < tolerance.min) {
                alert(`Peso digitado abaixo do minimo Aceitável: ${tolerance.min.toFixed(2)} Kg`);
                milheiroInput.style.borderColor = 'red';
            } else if (milheiroValue > tolerance.max) {
                alert(`Peso digitado acima do Máximo Aceitavel: ${tolerance.max.toFixed(2)} Kg`);
                milheiroInput.style.borderColor = 'red';
            } else {
                milheiroInput.style.borderColor = '#ccc';
            }
        } else {
            milheiroInput.style.borderColor = '#ccc';
        }
    }
    
    window.calcPreview = function() {
        const m=parseFloat(document.querySelector('[name=milheiro]').value)||0,
              rf=parseFloat(document.querySelector('[name=refugo_flexo]').value)||0,
              rpi=parseFloat(document.querySelector('[name=refugo_pre_impresso]').value)||0,
              rs=parseFloat(document.querySelector('[name=refugo_sos]').value)||0,
              raf=parseFloat(document.querySelector('[name=refugo_acerto_flexo]').value)||0,
              ras=parseFloat(document.querySelector('[name=refugo_acerto_sos]').value)||0,
              r=rf+rpi+rs+raf+ras, // Calcula refugo total como soma dos 5 campos
              q=parseInt(document.querySelector('[name=quantidade]').value)||0,
              qflexo=parseInt(document.querySelector('[name=quantidade_impressora]').value)||0,
              maquina=document.querySelector('[name=sos]').value, // Usa SOS ao invés de maquina
              formato=document.querySelector('[name=formato]').value,
              papel=document.querySelector('[name=papel]').value,
              qtd_cliches=parseInt(document.querySelector('[name=qtd_cliches]').value)||0;
        
        // Calcula tempo de produção SOS
        let tp1=0;const ip1=document.querySelector('[name=inicio_prod]').value,fp1=document.querySelector('[name=fim_prod]').value;if(ip1&&fp1){let d=getSeconds(fp1)-getSeconds(ip1);tp1=d<0?d+86400:d;}
        let tp2=0;if(document.getElementById('add_second_day').checked){const ip2=document.querySelector('[name=inicio_prod_2]').value,fp2=document.querySelector('[name=fim_prod_2]').value;if(ip2&&fp2){let d=getSeconds(fp2)-getSeconds(ip2);tp2=d<0?d+86400:d;}}
        const actual_prod_time_s=tp1+tp2;
        
        // Calcula tempo de acerto SOS
        let actual_setup_time_s=0;const ia=document.querySelector('[name=inicio_acerto]').value,fa=document.querySelector('[name=fim_acerto]').value;if(ia&&fa){let d=getSeconds(fa)-getSeconds(ia);actual_setup_time_s=d<0?d+86400:d;}
        
        // Calcula tempo de produção Impressora
        let actual_prod_time_impressora=0;
        const ip_imp=document.querySelector('[name=inicio_prod_impressora]').value;
        const fp_imp=document.querySelector('[name=fim_prod_impressora]').value;
        if(ip_imp&&fp_imp){let d=getSeconds(fp_imp)-getSeconds(ip_imp);actual_prod_time_impressora=d<0?d+86400:d;}
        
        // Calcula tempo de acerto Impressora
        let actual_setup_time_impressora=0;
        const ia_imp=document.querySelector('[name=inicio_acerto_impressora]').value;
        const fa_imp=document.querySelector('[name=fim_acerto_impressora]').value;
        if(ia_imp&&fa_imp){let d=getSeconds(fa_imp)-getSeconds(ia_imp);actual_setup_time_impressora=d<0?d+86400:d;}
        
        // Calcula refugos separados
        const rsos = rpi + rs + ras; // Refugo SOS (soma dos 3 tipos referentes a SOS)
        const rflexo = rf + raf; // Refugo Flexo (soma dos 2 tipos referentes a Flexo)
        
        // Calcula perdas, velocidade, peso e refugo
        const perdas_un=m>0?((rsos+rflexo)*1000)/m:0;
        const actual_speed_un_min=actual_prod_time_s>0?(q/(actual_prod_time_s/60)):0;
        const actual_speed_un_min_flexo=actual_prod_time_impressora>0?(qflexo/(actual_prod_time_impressora/60)):0;
        const kg_pu=m>0?m/1000:0;
        const peso_boas_sos=(q*kg_pu);
        const peso_boas_flexo=(qflexo*kg_pu);
        
        // Calcula porcentagem de refugo SOS
        const actual_scrap_pct_sos=(peso_boas_sos+rsos)>0?(rsos/(peso_boas_sos+rsos))*100:0;
        
        // Calcula porcentagem de refugo Impressora
        const actual_scrap_pct_flexo=(peso_boas_flexo+rflexo)>0?(rflexo/(peso_boas_flexo+rflexo))*100:0;
        
        // Para o gauge de refugo, usa o refugo SOS (que é o principal)
        const actual_scrap_pct=actual_scrap_pct_sos;
        
        let ideal_speed_un_h = 0;
        if (maquina === 'APLA-2R') {
            ideal_speed_un_h = 3000.0;
        } else if (maquina === 'IMPRESSORA') {
            ideal_speed_un_h = 8000.0;
        } else {
            ideal_speed_un_h = IDEAL_SPEED_RATES[formato] || 0;
        }
        const ideal_speed_un_min = ideal_speed_un_h / 60;

        const speed_performance=ideal_speed_un_min>0?(actual_speed_un_min/ideal_speed_un_min):0;
        const ideal_setup_time_s=(IDEAL_SETUP_TIMES_MIN[qtd_cliches]||0)*60;const setup_performance=actual_setup_time_s>0?(ideal_setup_time_s/actual_setup_time_s):1;
        let ideal_scrap_pct=1.0;if(['SOS 1','SOS 2','SOS 3'].includes(maquina)){ideal_scrap_pct=IDEAL_SCRAP_RATES_SOS_PCT[papel]||100.0;}
        const actual_yield=100.0-actual_scrap_pct_sos;const ideal_yield=100.0-ideal_scrap_pct;const scrap_performance=ideal_yield>0?(actual_yield/ideal_yield):0;
        const total_efficiency = (speed_performance * setup_performance * scrap_performance) * 100;
        
        // Atualiza os campos hidden com os valores calculados
        const refugoPctField = document.getElementById('refugo_pct');
        const refugoPctFlexoField = document.getElementById('refugo_pct_flexo');
        const eficienciaPctField = document.getElementById('eficiencia_pct');
        const velocidadeUnMinField = document.getElementById('velocidade_un_min');
        const velocidadeUnMinFlexoField = document.getElementById('velocidade_un_min_flexo');
        const perdasUnField = document.getElementById('perdas_un_hidden');
        const tempoProdSField = document.getElementById('tempo_prod_s');
        const tempoAcertoSField = document.getElementById('tempo_acerto_s');
        
        if(refugoPctField) refugoPctField.value = actual_scrap_pct_sos.toFixed(2);
        if(refugoPctFlexoField) refugoPctFlexoField.value = actual_scrap_pct_flexo.toFixed(2);
        if(eficienciaPctField) eficienciaPctField.value = total_efficiency.toFixed(2);
        if(velocidadeUnMinField) velocidadeUnMinField.value = actual_speed_un_min.toFixed(2);
        if(velocidadeUnMinFlexoField) velocidadeUnMinFlexoField.value = actual_speed_un_min_flexo.toFixed(2);
        if(perdasUnField) perdasUnField.value = perdas_un.toFixed(0);
        if(tempoProdSField) tempoProdSField.value = actual_prod_time_s;
        if(tempoAcertoSField) tempoAcertoSField.value = actual_setup_time_s;
    }

    // Inicializa campos numéricos com valores padrão ao carregar a página
    document.querySelectorAll('input[type=number]').forEach(function(campo) {
        // Se o campo estiver vazio ou não tiver valor definido
        if (campo.value === '' || campo.value === null || campo.value === undefined) {
            // Campos float (com step decimal) recebem 0.0
            if (campo.step && parseFloat(campo.step) < 1) {
                campo.value = '0.0';
            } else {
                // Campos int recebem 0
                campo.value = '0';
            }
        }
    });
    
    document.querySelectorAll('input,select').forEach(el=>{el.addEventListener('change',calcPreview); el.addEventListener('change', validateMilheiro)});
    document.querySelectorAll('input[type=number]').forEach(el => el.addEventListener('input', calcPreview));
    document.getElementById('add_second_day').addEventListener('change',function(){document.getElementById('second_day_fields').style.display=this.checked?'grid':'none';calcPreview();});
    if(!document.getElementById('data').value){document.getElementById('data').value="{{ lancamento.data if lancamento else '' }}"||new Date().toISOString().split('T')[0];}
    if(document.querySelector('[name=inicio_prod_2]').value){const c=document.getElementById('add_second_day');c.checked=true;document.getElementById('second_day_fields').style.display='grid';}
    calcPreview();
}); 