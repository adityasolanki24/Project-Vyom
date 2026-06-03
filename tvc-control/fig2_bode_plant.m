%% fig2_bode_plant.m
%  Openloop Bode plot of the bare plant G(s)
%  Shows the high plant gain and the gimbal servo resonance

tvc_params;

figure('Color','w','Position',[100 100 560 420]);
bode(G); grid on;
title('Bode plot of the bare plant G(s)');
set(findall(gcf,'Type','line'),'LineWidth',1.4);

exportgraphics(gcf,'fig_bode_plant.pdf','ContentType','vector');
disp('saved fig_bode_plant.pdf');
